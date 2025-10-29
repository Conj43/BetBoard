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
        print("🔍 FirebaseService: Attempting to fetch games from new path...")
        
        // Get the current date and format it as yyyy-MM-dd
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let currentDateStr = "2022-12-05" // Using the fixed date shown in screenshots
        
        // Use the correct path structure as shown in screenshots
        let gamesRef = db.collection("example_predictions").document(currentDateStr).collection("games")
        let snapshot = try await gamesRef.getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) game documents")
        
        let games = snapshot.documents.compactMap { document -> Game? in
            print("📄 Processing game document: \(document.documentID)")
            let data = document.data()
            print("📊 Game data keys: \(data.keys.sorted())")
            
            guard let teamA = data["team_A"] as? String,
                  let teamB = data["team_B"] as? String,
                  let dateString = data["date"] as? String,
                  let neutralSite = data["neutralSite"] as? Bool,
                  let gameId = data["game_id"] as? String else {
                print("❌ Missing required fields in game \(document.documentID)")
                print("   team_A: \(data["team_A"] ?? "nil")")
                print("   team_B: \(data["team_B"] ?? "nil")")
                print("   date: \(data["date"] ?? "nil")")
                print("   neutralSite: \(data["neutralSite"] ?? "nil")")
                print("   game_id: \(data["game_id"] ?? "nil")")
                return nil
            }
            
            // Convert the date string to Date object
            dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
            guard let gameDate = dateFormatter.date(from: dateString) else {
                print("❌ Failed to parse date: \(dateString)")
                return nil
            }
            
            // Uppercase team names
            let homeTeam = teamA.uppercased()
            let awayTeam = teamB.uppercased()
            
            // Parse game status
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
                id: gameId, // Using the game_id field
                homeTeam: homeTeam,
                awayTeam: awayTeam,
                date: gameDate,
                status: status,
                neutralSite: neutralSite
            )
            
            print("✅ Successfully created game: \(game.homeTeam) vs \(game.awayTeam) (Status: \(status))")
            return game
        }
        
        print("🎯 FirebaseService: Final games count: \(games.count)")
        return games
    }
    
    // MARK: - Teams
    func fetchTeams() async throws -> [Team] {
        print("🔍 FirebaseService: Attempting to fetch teams...")
        
        let snapshot = try await db.collection("teams").getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) team documents")
        
        let teams = snapshot.documents.compactMap { document -> Team? in
            print("📄 Processing team document: \(document.documentID)")
            let data = document.data()
            print("📊 Team data keys: \(data.keys.sorted())")
            
            guard let name = data["name"] as? String,
                  let shortName = data["shortName"] as? String,
                  let logoURL = data["logoURL"] as? String,
                  let conference = data["conference"] as? String else {
                print("❌ Missing required fields in team \(document.documentID)")
                print("   name: \(data["name"] ?? "nil")")
                print("   shortName: \(data["shortName"] ?? "nil")")
                print("   logoURL: \(data["logoURL"] ?? "nil")")
                print("   conference: \(data["conference"] ?? "nil")")
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
            
            print("✅ Successfully created team: \(team.name) (\(team.shortName))")
            return team
        }
        
        print("🎯 FirebaseService: Final teams count: \(teams.count)")
        return teams
    }
    
    func fetchBettingLines(for gameID: String) async throws -> BettingLines? {
        print("🔍 FirebaseService: Fetching betting lines for game: \(gameID)")
        
        // Extract date from gameID (assuming format includes date at the end like "20221205")
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard let dateComponent = gameIDComponents.last,
              dateComponent.count >= 8 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        // Format date from gameID (assuming format YYYYMMDD at end of gameID)
        let year = String(dateComponent.prefix(4))
        let month = String(dateComponent.dropFirst(4).prefix(2))
        let day = String(dateComponent.dropFirst(6).prefix(2))
        let formattedDate = "\(year)-\(month)-\(day)"
        
        do {
            // First, check if the game document exists
            let gameDoc = try await db.collection("example_predictions")
                                     .document(formattedDate)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            guard let gameData = gameDoc.data() else {
                print("❌ No game data found: \(gameID)")
                return nil
            }
            
            // Extract team names from the game document
            let teamA = gameData["team_A"] as? String ?? ""
            let teamB = gameData["team_B"] as? String ?? ""
            
            print("📊 Game teams: \(teamA) vs \(teamB)")
            
            // Access the sportsbookOdds subcollection for the game
            let sportsbookCollection = db.collection("example_predictions")
                                        .document(formattedDate)
                                        .collection("games")
                                        .document(gameID)
                                        .collection("sportsbookOdds")
            
            // Get all sportsbooks
            let sportsbookSnapshot = try await sportsbookCollection.getDocuments()
            
            if sportsbookSnapshot.documents.isEmpty {
                print("❌ No sportsbook data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Found \(sportsbookSnapshot.documents.count) sportsbooks for game: \(gameID)")
            
            // Preferred sportsbooks in order
            let preferredSportsbooks = ["draftkings", "fanduel", "betmgm", "caesars", "pointsbet", "barstool"]
            
            // Find the first available preferred sportsbook
            var selectedSportsbookDoc: DocumentSnapshot?
            
            for sportsbook in preferredSportsbooks {
                let potentialDoc = sportsbookSnapshot.documents.first { $0.documentID == sportsbook }
                if potentialDoc != nil {
                    selectedSportsbookDoc = potentialDoc
                    print("📱 Using \(sportsbook) as primary sportsbook")
                    break
                }
            }
            
            // If no preferred sportsbook found, use the first available
            if selectedSportsbookDoc == nil, let firstDoc = sportsbookSnapshot.documents.first {
                selectedSportsbookDoc = firstDoc
                print("📱 Using \(firstDoc.documentID) as fallback sportsbook")
            }
            
            guard let sportsbookDoc = selectedSportsbookDoc else {
                print("❌ No valid sportsbook data found")
                return nil
            }
            
            guard let sportsbookData = sportsbookDoc.data() else {
                print("❌ No data found in sportsbook document")
                return nil
            }
            
            let sportsbookName = sportsbookDoc.documentID
            
            // Process moneyline data
            var moneylineMap: [String: Double] = [:]
            if let moneylineData = sportsbookData["moneyline"] as? [String: Any] {
                // Based on the screenshot, moneyline data has team names as keys with odds as values
                for (team, odds) in moneylineData {
                    if let oddsValue = odds as? Double {
                        moneylineMap[team.uppercased()] = oddsValue
                    }
                }
            }
            
            // Process spread data
            var spreadMap: [String: Double] = [:]
            if let spreadData = sportsbookData["spread"] as? [String: Any] {
                // Based on the screenshot, spread data has entries like "CHARLESTONSOUTHERN +5.5": -105
                for (key, value) in spreadData {
                    if let odds = value as? Double {
                        spreadMap[key] = odds
                    }
                }
            }
            
            // Process total data
            var totalMap: [String: Double] = [:]
            if let totalData = sportsbookData["total"] as? [String: Any] {
                // Based on the screenshot, total data has entries like "Over 139.5": -105
                for (key, value) in totalData {
                    if let odds = value as? Double {
                        totalMap[key] = odds
                    }
                }
            }
            
            print("💰 Moneyline: \(moneylineMap)")
            print("📊 Spread: \(spreadMap)")
            print("🎯 Total: \(totalMap)")
            
            // Create BettingLines object
            let bettingLines = BettingLines(
                id: gameID + "-" + sportsbookName,
                gameID: gameID,
                moneyline: moneylineMap,
                spread: spreadMap,
                total: totalMap
            )
            
            print("✅ Successfully created betting lines for \(gameID) using \(sportsbookName)")
            return bettingLines
            
        } catch {
            print("❌ Error fetching betting lines for \(gameID): \(error)")
            throw error
        }
    }
    
    // MARK: - Predictions
    func fetchPredictionInfo(for gameID: String) async throws -> PredictionInfo? {
        print("🔍 FirebaseService: Fetching prediction for game: \(gameID)")
        
        // Extract date from gameID (assuming format includes date at the end like "20221205")
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard let dateComponent = gameIDComponents.last,
              dateComponent.count >= 8 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        // Format date from gameID (assuming format YYYYMMDD at end of gameID)
        let year = String(dateComponent.prefix(4))
        let month = String(dateComponent.dropFirst(4).prefix(2))
        let day = String(dateComponent.dropFirst(6).prefix(2))
        let formattedDate = "\(year)-\(month)-\(day)"
        
        do {
            // Access the correct document path
            let document = try await db.collection("example_predictions")
                                      .document(formattedDate)
                                      .collection("games")
                                      .document(gameID)
                                      .getDocument()
            
            guard document.exists, let data = document.data() else {
                print("❌ No prediction data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Prediction data keys: \(data.keys.sorted())")
            
            // Get team names
            let teamA = data["team_A"] as? String ?? ""
            let teamB = data["team_B"] as? String ?? ""
            
            // Initialize prediction containers
            var moneylineConfidence: Double = 0.0
            var moneylineBet: String? = nil
            
            var spreadConfidence: Double = 0.0
            var spreadBet: String? = nil
            
            var totalConfidence: Double = 0.0
            var totalBet: String? = nil
            
            // Process moneyline prediction
            if let moneyline = data["moneyline"] as? [String: Any],
               let predWinner = moneyline["pred_winner"] as? String,
               let pWinA = moneyline["p_win_A"] as? Double {
                
                // Calculate confidence based on predicted winner
                moneylineConfidence = (predWinner == "team_A") ? pWinA : (pWinA)
                moneylineConfidence *= 100 // Convert to percentage
                // Format the moneyline bet
                let teamName = (predWinner == teamA) ? teamA.uppercased() : teamB.uppercased()
                moneylineBet = teamName
                
                if teamName != teamA.uppercased() {
                    moneylineConfidence = 100 - moneylineConfidence
                }
            }
            
            // Process spread prediction
            if let spread = data["spread"] as? [String: Any],
               let pick = spread["pick"] as? String,
               let predMargin = spread["pred_margin"] as? Double {
                
                // Round pred_margin to nearest 0.5
                let roundedMargin = round(predMargin * 2) / 2
                
                // Get confidence
                if let probCover = spread["prob_cover"] as? Double {
                    spreadConfidence = probCover * 100
                }
                
                // Format the spread bet
                let teamName = (pick == teamA) ? teamA.uppercased() : teamB.uppercased()
                spreadBet = "\(teamName) \(roundedMargin > 0 ? "+" : "-")\(abs(roundedMargin))"
            }
            
            // Process total prediction
            if let total = data["total"] as? [String: Any],
               let pick = total["pick"] as? String,
               let predTotal = total["pred_total"] as? Double {
                
                // Round pred_total to nearest 0.5
                let roundedTotal = round(predTotal * 2) / 2
                
                // Get confidence
                if let probOver = total["prob_over"] as? Double {
                    totalConfidence = (pick == "OVER") ? probOver * 100 : (1 - probOver) * 100
                }
                
                // Format the total bet
                totalBet = "\(pick) \(roundedTotal)"
            }
            
            // For now, create a combined PredictionInfo with all three bet types
            // You may need to modify your PredictionInfo model to accommodate this
            let predictionInfo = PredictionInfo(
                moneylineConfidence: moneylineConfidence,
                moneylineBet: moneylineBet,
                
                spreadConfidence: spreadConfidence,
                spreadBet: spreadBet,
                
                totalConfidence: totalConfidence,
                totalBet: totalBet,
                
                analysis: nil // Not specified in requirements
            )
            
            print("✅ Successfully created predictions for \(gameID)")
            print("🏆 Moneyline: \(moneylineBet ?? "none") (\(moneylineConfidence)%)")
            print("📊 Spread: \(spreadBet ?? "none") (\(spreadConfidence)%)")
            print("📈 Total: \(totalBet ?? "none") (\(totalConfidence)%)")
            
            return predictionInfo
            
        } catch {
            print("❌ Error fetching prediction for \(gameID): \(error)")
            throw error
        }
    }
    
    func fetchBetSlips() async throws -> [BetSlip] {
        print("🔍 FirebaseService: Starting to fetch bet slips...")
        
        do {
            let games = try await fetchGames()
            let teams = try await fetchTeams()
            
            print("📊 Fetched \(games.count) games and \(teams.count) teams")
            
            // Create team lookup dictionary
            var teamLookup: [String: Team] = [:]
            for team in teams {
                teamLookup[team.shortName] = team
                teamLookup[team.id] = team  // Also add by ID in case it's used
                print("🔗 Added team to lookup: \(team.shortName) -> \(team.name)")
            }
            
            var betSlips: [BetSlip] = []
            
            print("🎮 Processing \(games.count) games...")
            for game in games {
                print("🎮 Processing game: \(game.homeTeam) vs \(game.awayTeam) (ID: \(game.id))")
                
                guard let homeTeam = teamLookup[game.homeTeam],
                      let awayTeam = teamLookup[game.awayTeam] else {
                    print("❌ Could not find teams for game: \(game.homeTeam) vs \(game.awayTeam)")
                    print("   Available teams: \(teamLookup.keys.sorted())")
                    continue
                }
                
                print("✅ Found teams: \(homeTeam.name) vs \(awayTeam.name)")
                
                // Fetch all betting lines for this game
                if let allBettingLines = try await fetchAllBettingLines(for: game.id) {
                    print("💰 Found betting lines for \(game.id)")
                    
                    // Try to fetch prediction info
                    let predictionInfo = try await fetchPredictionInfo(for: game.id)
                    if predictionInfo != nil {
                        print("🧠 Found prediction info for \(game.id)")
                    } else {
                        print("⚠️ No prediction info for \(game.id)")
                    }
                    
                    // Use DraftKings as default fallback
                    let defaultBettingLines = allBettingLines.draftkings ??
                                            allBettingLines.fanduel ??
                                            allBettingLines.betmgm ??
                                            BettingLines(id: game.id, gameID: game.id, moneyline: [:], spread: [:], total: [:])
                    
                    let betSlip = BetSlip(
                        id: game.id,
                        gameID: game.id,
                        sportsbook: .draftkings, // Default sportsbook
                        homeTeam: homeTeam,
                        awayTeam: awayTeam,
                        gameTime: game.date,
                        bettingLines: defaultBettingLines,
                        allBettingLines: allBettingLines,
                        predictionInfo: predictionInfo,
                        neutralSite: game.neutralSite
                    )
                    
                    betSlips.append(betSlip)
                    print("✅ Created bet slip for: \(game.homeTeam) vs \(game.awayTeam)")
                } else {
                    print("⚠️ No betting lines found for game: \(game.id)")
                }
            }
            
            print("🎯 FirebaseService: Final bet slips count: \(betSlips.count)")
            
            // Log first few bet slips for debugging
            for (index, betSlip) in betSlips.prefix(3).enumerated() {
                print("📋 Bet Slip \(index + 1):")
                print("   ID: \(betSlip.id)")
                print("   Teams: \(betSlip.homeTeam.shortName) vs \(betSlip.awayTeam.shortName)")
                print("   Game Time: \(betSlip.formattedGameTime)")
                print("   Has Prediction: \(betSlip.predictionInfo != nil)")
                if let predictionInfo = betSlip.predictionInfo {
                    print("   Moneyline: \(predictionInfo.moneylineBet ?? "none") (\(predictionInfo.moneylineConfidence)%)")
                    print("   Spread: \(predictionInfo.spreadBet ?? "none") (\(predictionInfo.spreadConfidence)%)")
                    print("   Total: \(predictionInfo.totalBet ?? "none") (\(predictionInfo.totalConfidence)%)")
                }
                print("   Available Sportsbooks: \(availableSportsbooks(for: betSlip.allBettingLines))")
            }
            
            return betSlips
            
        } catch {
            print("❌ Error in fetchBetSlips: \(error)")
            throw error
        }
    }
    // MARK: - User Bets
    func fetchUserBets(for userID: String) async throws -> [Bet] {
        print("🔍 FirebaseService: Fetching user bets for: \(userID)")
        
        do {
            let snapshot = try await db.collection("users").document(userID).collection("bets").getDocuments()
            print("📊 Found \(snapshot.documents.count) user bet documents")
            
            let bets = snapshot.documents.compactMap { document -> Bet? in
                let data = document.data()
                print("📄 Processing bet document: \(document.documentID)")
                print("📊 Bet data keys: \(data.keys.sorted())")
                
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
                    print("   gameID: \(data["gameID"] ?? "nil")")
                    print("   type: \(data["type"] ?? "nil")")
                    print("   selection: \(data["selection"] ?? "nil")")
                    print("   odds: \(data["odds"] ?? "nil")")
                    print("   amount: \(data["amount"] ?? "nil")")
                    print("   result: \(data["result"] ?? "nil")")
                    print("   placedAt: \(data["placedAt"] ?? "nil")")
                    return nil
                }
                
                let bet = Bet(
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
                
                print("✅ Created bet: \(bet.selection) - $\(bet.amount) - \(bet.result.rawValue)")
                return bet
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
        print("🔍 FirebaseService: Adding user bet: \(bet.selection) for $\(bet.amount)")
        
        let betData: [String: Any] = [
            "gameID": bet.gameID,
            "type": bet.type.rawValue,
            "selection": bet.selection,
            "odds": bet.odds,
            "amount": bet.amount,
            "result": bet.result.rawValue,
            "placedAt": Timestamp(date: bet.placedAt)
        ]
        
        do {
            try await db.collection("users").document(bet.userID).collection("bets").addDocument(data: betData)
            print("✅ Successfully added user bet")
        } catch {
            print("❌ Error adding user bet: \(error)")
            throw error
        }
    }
    
    // MARK: - Delete User Bet
    func deleteUserBet(betID: String, userID: String) async throws {
        print("🔍 FirebaseService: Deleting bet \(betID) for user \(userID)")
        
        do {
            try await db.collection("users").document(userID).collection("bets").document(betID).delete()
            print("✅ Successfully deleted user bet")
        } catch {
            print("❌ Error deleting user bet: \(error)")
            throw error
        }
    }
    
    // MARK: - Update Bet Result
    func updateBetResult(betID: String, userID: String, result: BetResult) async throws {
        print("🔍 FirebaseService: Updating bet \(betID) result to \(result.rawValue)")
        
        do {
            try await db.collection("users").document(userID).collection("bets").document(betID).updateData([
                "result": result.rawValue
            ])
            print("✅ Successfully updated bet result")
        } catch {
            print("❌ Error updating bet result: \(error)")
            throw error
        }
    }
    
    // MARK: - User Settings
    func fetchUserSettings(for userID: String) async throws -> AppSettings? {
        print("🔍 FirebaseService: Fetching user settings for: \(userID)")
        
        do {
            let document = try await db.collection("users").document(userID).getDocument()
            
            guard document.exists, let data = document.data() else {
                print("❌ No user settings found for: \(userID)")
                return nil
            }
            
            print("📊 User settings data keys: \(data.keys.sorted())")
            
            let notificationsEnabled = data["notificationsEnabled"] as? Bool ?? true
            let darkModeEnabled = data["darkModeEnabled"] as? Bool ?? false
            let oddsFormatString = data["preferredOddsFormat"] as? String ?? "american"
            let preferredOddsFormat = OddsFormat(rawValue: oddsFormatString) ?? .american
            
            let settings = AppSettings(
                userID: userID,
                notificationsEnabled: notificationsEnabled,
                darkModeEnabled: darkModeEnabled,
                preferredOddsFormat: preferredOddsFormat
            )
            
            print("✅ Successfully fetched user settings")
            return settings
            
        } catch {
            print("❌ Error fetching user settings: \(error)")
            throw error
        }
    }
    
    // MARK: - Update User Settings
    func updateUserSettings(_ settings: AppSettings) async throws {
        print("🔍 FirebaseService: Updating user settings for: \(settings.userID)")
        
        let settingsData: [String: Any] = [
            "notificationsEnabled": settings.notificationsEnabled,
            "darkModeEnabled": settings.darkModeEnabled,
            "preferredOddsFormat": settings.preferredOddsFormat.rawValue
        ]
        
        do {
            try await db.collection("users").document(settings.userID).setData(settingsData, merge: true)
            print("✅ Successfully updated user settings")
        } catch {
            print("❌ Error updating user settings: \(error)")
            throw error
        }
    }
    func fetchAllBettingLines(for gameID: String) async throws -> AllSportsbookLines? {
        print("🔍 FirebaseService: Fetching all betting lines for game: \(gameID)")
        
        // Extract date from gameID (assuming format includes date at the end like "20221205")
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard let dateComponent = gameIDComponents.last,
              dateComponent.count >= 8 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        // Format date from gameID (assuming format YYYYMMDD at end of gameID)
        let year = String(dateComponent.prefix(4))
        let month = String(dateComponent.dropFirst(4).prefix(2))
        let day = String(dateComponent.dropFirst(6).prefix(2))
        let formattedDate = "\(year)-\(month)-\(day)"
        
        do {
            // First, check if the game document exists
            let gameDoc = try await db.collection("example_predictions")
                                     .document(formattedDate)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            // Access the sportsbookOdds subcollection for the game
            let sportsbookCollection = db.collection("example_predictions")
                                        .document(formattedDate)
                                        .collection("games")
                                        .document(gameID)
                                        .collection("sportsbookOdds")
            
            // Get all sportsbooks
            let sportsbookSnapshot = try await sportsbookCollection.getDocuments()
            
            if sportsbookSnapshot.documents.isEmpty {
                print("❌ No sportsbook data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Found \(sportsbookSnapshot.documents.count) sportsbooks for game: \(gameID)")
            
            // Initialize variables for each sportsbook
            var draftkingsLines: BettingLines?
            var betmgmLines: BettingLines?
            var fanduelLines: BettingLines?
            var caesarsLines: BettingLines?
            var pointsbetLines: BettingLines?
            var barstoolLines: BettingLines?
            
            // Process each sportsbook document
            for sportsbookDoc in sportsbookSnapshot.documents {
                let sportsbookName = sportsbookDoc.documentID
                let sportsbookData = sportsbookDoc.data()
                
                print("🏢 Processing sportsbook: \(sportsbookName)")
                
                // Process moneyline data
                var moneylineMap: [String: Double] = [:]
                if let moneylineData = sportsbookData["moneyline"] as? [String: Any] {
                    for (team, odds) in moneylineData {
                        if let oddsValue = odds as? Double {
                            moneylineMap[team.uppercased()] = oddsValue
                        }
                    }
                }
                
                // Process spread data
                var spreadMap: [String: Double] = [:]
                if let spreadData = sportsbookData["spread"] as? [String: Any] {
                    for (key, value) in spreadData {
                        if let odds = value as? Double {
                            spreadMap[key] = odds
                        }
                    }
                }
                
                // Process total data
                var totalMap: [String: Double] = [:]
                if let totalData = sportsbookData["total"] as? [String: Any] {
                    for (key, value) in totalData {
                        if let odds = value as? Double {
                            totalMap[key] = odds
                        }
                    }
                }
                
                // Create BettingLines object for this sportsbook
                let bettingLines = BettingLines(
                    id: gameID + "-" + sportsbookName,
                    gameID: gameID,
                    moneyline: moneylineMap,
                    spread: spreadMap,
                    total: totalMap
                )
                
                // Assign to appropriate sportsbook variable
                switch sportsbookName.lowercased() {
                case "draftkings":
                    draftkingsLines = bettingLines
                    print("✅ Processed DraftKings odds")
                case "betmgm":
                    betmgmLines = bettingLines
                    print("✅ Processed BetMGM odds")
                case "fanduel":
                    fanduelLines = bettingLines
                    print("✅ Processed FanDuel odds")
                case "caesars":
                    caesarsLines = bettingLines
                    print("✅ Processed Caesars odds")
                case "pointsbet":
                    pointsbetLines = bettingLines
                    print("✅ Processed PointsBet odds")
                case "barstool":
                    barstoolLines = bettingLines
                    print("✅ Processed Barstool odds")
                default:
                    print("⚠️ Unknown sportsbook: \(sportsbookName)")
                }
            }
            
            // Create AllSportsbookLines object
            let allLines = AllSportsbookLines(
                draftkings: draftkingsLines,
                betmgm: betmgmLines,
                fanduel: fanduelLines,
                caesars: caesarsLines,
                pointsbet: pointsbetLines,
                barstool: barstoolLines
            )
            
            print("✅ Successfully created all betting lines for \(gameID)")
            return allLines
            
        } catch {
            print("❌ Error fetching all betting lines for \(gameID): \(error)")
            throw error
        }
    }
    // Helper function to list available sportsbooks
    private func availableSportsbooks(for allLines: AllSportsbookLines?) -> [String] {
        guard let allLines = allLines else { return [] }
        var sportsbooks: [String] = []
        if allLines.draftkings != nil { sportsbooks.append("DraftKings") }
        if allLines.betmgm != nil { sportsbooks.append("BetMGM") }
        if allLines.fanduel != nil { sportsbooks.append("FanDuel") }
        if allLines.caesars != nil { sportsbooks.append("Caesars") }
        if allLines.pointsbet != nil { sportsbooks.append("PointsBet") }
        if allLines.barstool != nil { sportsbooks.append("Barstool") }
        return sportsbooks
    }
}
