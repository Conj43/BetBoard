//
//  GameResultUpdater.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/27/25.
//

import Foundation
import FirebaseFirestore
import FirebaseAuth

@MainActor
class GameResultUpdater: ObservableObject {
    @Published var isUpdating = false
    @Published var updateMessage: String?
    @Published var availableGames: [Game] = []
    
    private let db = Firestore.firestore()
    private let firebaseService = FirebaseService()
    
    func loadAvailableGames() async {
        do {
            let games = try await firebaseService.fetchGames()
            await MainActor.run {
                self.availableGames = games.filter { game in
                    // Only show games that haven't been finalized yet
                    switch game.status {
                    case .final:
                        return false
                    default:
                        return true
                    }
                }
            }
        } catch {
            await MainActor.run {
                self.updateMessage = "Failed to load games: \(error.localizedDescription)"
            }
        }
    }
    
    func updateGameResult(gameID: String, homeScore: Int, awayScore: Int) async {
        isUpdating = true
        updateMessage = nil
        
        do {
            // Update the game status in Firebase
            let gameRef = db.collection("games").document(gameID)
            try await gameRef.updateData([
                "status": [
                    "state": "FINAL",
                    "homeScore": homeScore,
                    "awayScore": awayScore
                ]
            ])
            
            // Now update all bets for this game
            await updateAllBetsForGame(gameID: gameID, homeScore: homeScore, awayScore: awayScore)
            
            await MainActor.run {
                self.updateMessage = "Successfully updated game result and all related bets!"
                self.isUpdating = false
            }
            
        } catch {
            await MainActor.run {
                self.updateMessage = "Failed to update game: \(error.localizedDescription)"
                self.isUpdating = false
            }
        }
    }
    
    private func updateAllBetsForGame(gameID: String, homeScore: Int, awayScore: Int) async {
        do {
            // First get the game info to know which teams are home/away
            let gameDoc = try await db.collection("games").document(gameID).getDocument()
            guard let gameData = gameDoc.data(),
                  let homeTeam = gameData["homeTeam"] as? String,
                  let awayTeam = gameData["awayTeam"] as? String else {
                print("Could not get game team info")
                return
            }
            
            // Get all users
            let usersSnapshot = try await db.collection("users").getDocuments()
            
            for userDoc in usersSnapshot.documents {
                let userID = userDoc.documentID
                
                // Get all bets for this user
                let betsSnapshot = try await db.collection("users")
                    .document(userID)
                    .collection("bets")
                    .whereField("gameID", isEqualTo: gameID)
                    .getDocuments()
                
                // Update each bet
                for betDoc in betsSnapshot.documents {
                    let betData = betDoc.data()
                    
                    guard let typeString = betData["type"] as? String,
                          let betType = BetType(rawValue: typeString),
                          let selection = betData["selection"] as? String else {
                        continue
                    }
                    
                    let result = calculateBetResult(
                        betType: betType,
                        selection: selection,
                        homeScore: homeScore,
                        awayScore: awayScore,
                        homeTeam: homeTeam,
                        awayTeam: awayTeam
                    )
                    
                    print("🔍 Calculating bet: \(selection)")
                    print("📊 Game result: \(awayTeam) \(awayScore) @ \(homeTeam) \(homeScore)")
                    print("✅ Bet result: \(result.rawValue)")
                    
                    // Update the bet result
                    try await db.collection("users")
                        .document(userID)
                        .collection("bets")
                        .document(betDoc.documentID)
                        .updateData(["result": result.rawValue])
                }
            }
        } catch {
            print("Error updating bets: \(error)")
        }
    }
    
    private func calculateBetResult(betType: BetType, selection: String, homeScore: Int, awayScore: Int, homeTeam: String, awayTeam: String) -> BetResult {
        print("🎯 Calculating bet result for: \(selection)")
        print("🏀 Game: \(awayTeam) \(awayScore) @ \(homeTeam) \(homeScore)")
        
        switch betType {
        case .moneyline:
            return calculateMoneylineResult(selection: selection, homeScore: homeScore, awayScore: awayScore, homeTeam: homeTeam, awayTeam: awayTeam)
        case .spread:
            return calculateSpreadResult(selection: selection, homeScore: homeScore, awayScore: awayScore, homeTeam: homeTeam, awayTeam: awayTeam)
        case .total:
            return calculateTotalResult(selection: selection, homeScore: homeScore, awayScore: awayScore)
        }
    }
    
    private func calculateMoneylineResult(selection: String, homeScore: Int, awayScore: Int, homeTeam: String, awayTeam: String) -> BetResult {
        // Selection format: "UNC ML" or "DUKE ML"
        let teamFromSelection = selection.replacingOccurrences(of: " ML", with: "").trimmingCharacters(in: .whitespaces)
        
        print("💰 Moneyline bet on: \(teamFromSelection)")
        
        let winner: String
        if homeScore > awayScore {
            winner = homeTeam
            print("🏆 Winner: \(homeTeam) (home team)")
        } else if awayScore > homeScore {
            winner = awayTeam
            print("🏆 Winner: \(awayTeam) (away team)")
        } else {
            print("🤝 Tie game - Push")
            return .push
        }
        
        let result: BetResult = teamFromSelection.uppercased() == winner.uppercased() ? .won : .lost
        print("📈 Bet result: \(result.rawValue)")
        return result
    }
    
    private func calculateSpreadResult(selection: String, homeScore: Int, awayScore: Int, homeTeam: String, awayTeam: String) -> BetResult {
        // Selection format: "DUKE -3.5" or "UNC +3.5"
        print("📊 Spread bet: \(selection)")
        
        // Extract team and spread
        let components = selection.components(separatedBy: " ")
        guard components.count >= 2 else {
            print("❌ Invalid spread format")
            return .lost
        }
        
        let teamFromSelection = components[0].trimmingCharacters(in: .whitespaces)
        let spreadString = components[1]
        
        guard let spread = Double(spreadString) else {
            print("❌ Could not parse spread: \(spreadString)")
            return .lost
        }
        
        print("🎯 Team: \(teamFromSelection), Spread: \(spread)")
        
        // Determine if betting on home or away team
        let isHomeBet = teamFromSelection.uppercased() == homeTeam.uppercased()
        let finalScore: Double
        
        if isHomeBet {
            // Betting on home team
            finalScore = Double(homeScore) + spread
            let covered = finalScore > Double(awayScore)
            print("🏠 Home bet: \(homeScore) + \(spread) = \(finalScore) vs \(awayScore)")
            print("✅ Covered: \(covered)")
            return covered ? .won : .lost
        } else {
            // Betting on away team
            finalScore = Double(awayScore) + spread
            let covered = finalScore > Double(homeScore)
            print("✈️ Away bet: \(awayScore) + \(spread) = \(finalScore) vs \(homeScore)")
            print("✅ Covered: \(covered)")
            return covered ? .won : .lost
        }
    }
    
    private func calculateTotalResult(selection: String, homeScore: Int, awayScore: Int) -> BetResult {
        // Selection format: "Over 145.5" or "Under 145.5"
        print("📊 Total bet: \(selection)")
        
        let gameTotal = Double(homeScore + awayScore)
        print("🏀 Game total: \(gameTotal)")
        
        // Extract the total number
        let components = selection.components(separatedBy: " ")
        guard components.count >= 2,
              let betTotal = Double(components[1]) else {
            print("❌ Could not parse total")
            return .lost
        }
        
        let isOver = selection.uppercased().contains("OVER")
        print("📈 Bet total: \(betTotal), Is Over: \(isOver)")
        
        if gameTotal == betTotal {
            print("🤝 Push - exact total")
            return .push
        } else if isOver {
            let won = gameTotal > betTotal
            print("📈 Over bet result: \(won)")
            return won ? .won : .lost
        } else {
            let won = gameTotal < betTotal
            print("📉 Under bet result: \(won)")
            return won ? .won : .lost
        }
    }
}

// MARK: - Simplified Bet Result Calculator for Testing
extension GameResultUpdater {
    func calculateBetResultSimplified(betType: BetType, selection: String, homeScore: Int, awayScore: Int) -> BetResult {
        switch betType {
        case .moneyline:
            // Simple logic for demo - in real app you'd match team names properly
            if homeScore > awayScore {
                return selection.uppercased().contains("DUKE") ? .won : .lost
            } else {
                return selection.uppercased().contains("UNC") ? .won : .lost
            }
            
        case .spread:
            // Extract spread value
            if let range = selection.range(of: #"[+-]\d+\.?\d*"#, options: .regularExpression) {
                let spreadString = String(selection[range])
                if let spread = Double(spreadString) {
                    let coveredSpread = Double(homeScore - awayScore) + spread
                    return coveredSpread > 0 ? .won : (coveredSpread == 0 ? .push : .lost)
                }
            }
            return .lost
            
        case .total:
            // Extract total value
            if let range = selection.range(of: #"\d+\.?\d*"#, options: .regularExpression) {
                let totalString = String(selection[range])
                if let total = Double(totalString) {
                    let gameTotal = Double(homeScore + awayScore)
                    let isOver = selection.uppercased().contains("OVER")
                    
                    if gameTotal == total {
                        return .push
                    } else if isOver {
                        return gameTotal > total ? .won : .lost
                    } else {
                        return gameTotal < total ? .won : .lost
                    }
                }
            }
            return .lost
        }
    }
}
