//
//  FirebaseService.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import FirebaseFirestore
import FirebaseAuth
import Combine

@MainActor
class FirebaseService: ObservableObject {
    private let db = Firestore.firestore()
    
    // MARK: - Games
    func fetchGames() async throws -> [Game] {
        print("🔍 Attempting to fetch games...")
        
        let snapshot = try await db.collection("games").getDocuments()
        print("✅ Successfully fetched \(snapshot.documents.count) game documents")
        
        let games = snapshot.documents.compactMap { document -> Game? in
            print("📄 Processing game document: \(document.documentID)")
            let data = document.data()
            print("📊 Game data: \(data)")
            
            guard let homeTeam = data["homeTeam"] as? String,
                  let awayTeam = data["awayTeam"] as? String,
                  let dateTimestamp = data["date"] as? Timestamp,
                  let neutralSite = data["neutralSite"] as? Bool else {
                print("❌ Missing required fields in game \(document.documentID)")
                return nil
            }
            
            let status: GameStatus
            if let statusData = data["status"] as? [String: Any],
               let state = statusData["state"] as? String {
                switch state {
                case "NP":
                    status = .notPlayed
                case "IP":
                    status = .inProgress
                case "FINAL":
                    if let homeScore = statusData["homeScore"] as? Int,
                       let awayScore = statusData["awayScore"] as? Int {
                        status = .final(home: homeScore, away: awayScore)
                    } else {
                        status = .notPlayed
                    }
                default:
                    status = .notPlayed
                }
            } else {
                status = .notPlayed
            }
            
            let game = Game(
                id: document.documentID,
                homeTeam: homeTeam,
                awayTeam: awayTeam,
                date: dateTimestamp.dateValue(),
                status: status,
                neutralSite: neutralSite
            )
            
            print("✅ Successfully created game: \(game.homeTeam) vs \(game.awayTeam)")
            return game
        }
        
        print("🎯 Final games count: \(games.count)")
        return games
    }
    
    // MARK: - Teams
    func fetchTeams() async throws -> [Team] {
        print("🔍 Attempting to fetch teams...")
        
        let snapshot = try await db.collection("teams").getDocuments()
        print("✅ Successfully fetched \(snapshot.documents.count) team documents")
        
        let teams = snapshot.documents.compactMap { document -> Team? in
            print("📄 Processing team document: \(document.documentID)")
            let data = document.data()
            
            guard let name = data["name"] as? String,
                  let shortName = data["shortName"] as? String,
                  let logoURL = data["logoURL"] as? String,
                  let conference = data["conference"] as? String else {
                print("❌ Missing required fields in team \(document.documentID)")
                return nil
            }
            
            let recordData = data["record"] as? [String: Any]
            let wins = recordData?["wins"] as? Int ?? 0
            let losses = recordData?["losses"] as? Int ?? 0
            
            let team = Team(
                id: document.documentID,
                name: name,
                shortName: shortName,
                logoURL: logoURL,
                record: TeamRecord(wins: wins, losses: losses),
                conference: conference,
                ranking: data["ranking"] as? Int,
                colorHex: data["colorHex"] as? String
            )
            
            print("✅ Successfully created team: \(team.name)")
            return team
        }
        
        print("🎯 Final teams count: \(teams.count)")
        return teams
    }
    
    // MARK: - Betting Lines
    func fetchBettingLines(for gameID: String) async throws -> BettingLines? {
        print("🔍 Fetching betting lines for game: \(gameID)")
        
        do {
            let document = try await db.collection("bettingLines").document(gameID).getDocument()
            
            guard let data = document.data() else {
                print("❌ No betting lines data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Betting lines data: \(data)")
            
            let moneyline = data["moneyline"] as? [String: Double] ?? [:]
            let spread = data["spread"] as? [String: Double] ?? [:]
            let total = data["total"] as? [String: Double] ?? [:]
            
            let bettingLines = BettingLines(
                id: document.documentID,
                gameID: gameID,
                moneyline: moneyline,
                spread: spread,
                total: total
            )
            
            print("✅ Successfully created betting lines for \(gameID)")
            return bettingLines
            
        } catch {
            print("❌ Error fetching betting lines for \(gameID): \(error)")
            throw error
        }
    }
    
    // MARK: - Predictions
    func fetchPredictionInfo(for gameID: String) async throws -> PredictionInfo? {
        print("🔍 Fetching prediction for game: \(gameID)")
        
        do {
            let document = try await db.collection("predictions").document(gameID).getDocument()
            
            guard let data = document.data() else {
                print("❌ No prediction data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Prediction data: \(data)")
            
            let confidence = data["confidence"] as? Double ?? 0.0
            let recommendedBet = data["recommendedBet"] as? String
            let analysis = data["analysis"] as? String
            
            let predictionInfo = PredictionInfo(
                confidence: confidence,
                recommendedBet: recommendedBet,
                analysis: analysis
            )
            
            print("✅ Successfully created prediction for \(gameID)")
            return predictionInfo
            
        } catch {
            print("❌ Error fetching prediction for \(gameID): \(error)")
            throw error
        }
    }
    
    // MARK: - Bet Slips
    func fetchBetSlips() async throws -> [BetSlip] {
        print("🔍 Starting to fetch bet slips...")
        
        do {
            let games = try await fetchGames()
            let teams = try await fetchTeams()
            
            print("📊 Fetched \(games.count) games and \(teams.count) teams")
            
            // Create team lookup dictionary
            var teamLookup: [String: Team] = [:]
            for team in teams {
                teamLookup[team.shortName] = team
                print("📝 Added team to lookup: \(team.shortName) -> \(team.name)")
            }
            
            var betSlips: [BetSlip] = []
            
            for game in games {
                print("🎮 Processing game: \(game.homeTeam) vs \(game.awayTeam)")
                
                guard let homeTeam = teamLookup[game.homeTeam],
                      let awayTeam = teamLookup[game.awayTeam] else {
                    print("❌ Could not find teams for game: \(game.homeTeam) vs \(game.awayTeam)")
                    continue
                }
                
                // Fetch betting lines for this game
                if let bettingLines = try await fetchBettingLines(for: game.id) {
                    // Try to fetch prediction info
                    let predictionInfo = try await fetchPredictionInfo(for: game.id)
                    
                    let betSlip = BetSlip(
                        id: game.id,
                        gameID: game.id,
                        sportsbook: .draftkings, // Default sportsbook
                        homeTeam: homeTeam,
                        awayTeam: awayTeam,
                        gameTime: game.date,
                        bettingLines: bettingLines,
                        predictionInfo: predictionInfo,
                        neutralSite: game.neutralSite
                    )
                    
                    betSlips.append(betSlip)
                    print("✅ Created bet slip for: \(game.homeTeam) vs \(game.awayTeam)")
                } else {
                    print("⚠️ No betting lines found for game: \(game.id)")
                }
            }
            
            print("🎯 Final bet slips count: \(betSlips.count)")
            return betSlips
            
        } catch {
            print("❌ Error in fetchBetSlips: \(error)")
            throw error
        }
    }
    
    // MARK: - User Bets (Mock for testing)
    func fetchUserBets(for userID: String) async throws -> [Bet] {
        print("🔍 Fetching user bets for: \(userID)")
        
        do {
            let snapshot = try await db.collection("users").document(userID).collection("bets").getDocuments()
            print("📊 Found \(snapshot.documents.count) user bet documents")
            
            let bets = snapshot.documents.compactMap { document -> Bet? in
                let data = document.data()
                
                guard let gameID = data["gameID"] as? String,
                      let typeString = data["type"] as? String,
                      let type = BetType(rawValue: typeString),
                      let selection = data["selection"] as? String,
                      let odds = data["odds"] as? Double,
                      let amount = data["amount"] as? Double,
                      let resultString = data["result"] as? String,
                      let result = BetResult(rawValue: resultString),
                      let placedAtTimestamp = data["placedAt"] as? Timestamp else {
                    print("❌ Invalid bet data in document: \(document.documentID)")
                    return nil
                }
                
                return Bet(
                    id: document.documentID,
                    userID: userID,
                    gameID: gameID,
                    type: type,
                    selection: selection,
                    odds: odds,
                    amount: amount,
                    result: result,
                    placedAt: placedAtTimestamp.dateValue()
                )
            }
            
            print("✅ Successfully fetched \(bets.count) user bets")
            return bets
            
        } catch {
            print("❌ Error fetching user bets: \(error)")
            // Return empty array instead of throwing for testing
            return []
        }
    }
    
    // MARK: - Add User Bet
    func addUserBet(_ bet: Bet) async throws {
        let betData: [String: Any] = [
            "gameID": bet.gameID,
            "type": bet.type.rawValue,
            "selection": bet.selection,
            "odds": bet.odds,
            "amount": bet.amount,
            "result": bet.result.rawValue,
            "placedAt": Timestamp(date: bet.placedAt)
        ]
        
        try await db.collection("users").document(bet.userID).collection("bets").addDocument(data: betData)
    }
    
    // MARK: - Delete User Bet
    func deleteUserBet(betID: String, userID: String) async throws {
        try await db.collection("users").document(userID).collection("bets").document(betID).delete()
    }
    
    // MARK: - Update Bet Result
    func updateBetResult(betID: String, userID: String, result: BetResult) async throws {
        try await db.collection("users").document(userID).collection("bets").document(betID).updateData([
            "result": result.rawValue
        ])
    }
    
    // MARK: - User Settings
    func fetchUserSettings(for userID: String) async throws -> AppSettings? {
        let document = try await db.collection("users").document(userID).getDocument()
        
        guard let data = document.data() else { return nil }
        
        let notificationsEnabled = data["notificationsEnabled"] as? Bool ?? true
        let darkModeEnabled = data["darkModeEnabled"] as? Bool ?? false
        let oddsFormatString = data["preferredOddsFormat"] as? String ?? "american"
        let preferredOddsFormat = OddsFormat(rawValue: oddsFormatString) ?? .american
        
        return AppSettings(
            userID: userID,
            notificationsEnabled: notificationsEnabled,
            darkModeEnabled: darkModeEnabled,
            preferredOddsFormat: preferredOddsFormat
        )
    }
    
    // MARK: - Update User Settings
    func updateUserSettings(_ settings: AppSettings) async throws {
        let settingsData: [String: Any] = [
            "notificationsEnabled": settings.notificationsEnabled,
            "darkModeEnabled": settings.darkModeEnabled,
            "preferredOddsFormat": settings.preferredOddsFormat.rawValue
        ]
        
        try await db.collection("users").document(settings.userID).setData(settingsData, merge: true)
    }
}
