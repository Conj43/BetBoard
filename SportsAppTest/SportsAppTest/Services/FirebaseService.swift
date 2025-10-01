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
        print("🔍 FirebaseService: Attempting to fetch games...")
        
        let snapshot = try await db.collection("games").getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) game documents")
        
        let games = snapshot.documents.compactMap { document -> Game? in
            print("📄 Processing game document: \(document.documentID)")
            let data = document.data()
            print("📊 Game data keys: \(data.keys.sorted())")
            
            guard let homeTeam = data["homeTeam"] as? String,
                  let awayTeam = data["awayTeam"] as? String,
                  let dateTimestamp = data["date"] as? Timestamp,
                  let neutralSite = data["neutralSite"] as? Bool else {
                print("❌ Missing required fields in game \(document.documentID)")
                print("   homeTeam: \(data["homeTeam"] ?? "nil")")
                print("   awayTeam: \(data["awayTeam"] ?? "nil")")
                print("   date: \(data["date"] ?? "nil")")
                print("   neutralSite: \(data["neutralSite"] ?? "nil")")
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
    
    // MARK: - Betting Lines
    func fetchBettingLines(for gameID: String) async throws -> BettingLines? {
        print("🔍 FirebaseService: Fetching betting lines for game: \(gameID)")
        
        do {
            let document = try await db.collection("bettingLines").document(gameID).getDocument()
            
            guard document.exists, let data = document.data() else {
                print("❌ No betting lines data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Betting lines data keys: \(data.keys.sorted())")
            
            // Check if data has the expected flat structure
            if let moneyline = data["moneyline"] as? [String: Double],
               let spread = data["spread"] as? [String: Double],
               let total = data["total"] as? [String: Double] {
                
                // Use existing flat structure
                print("✅ Using flat betting lines structure")
                let bettingLines = BettingLines(
                    id: document.documentID,
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                
                print("✅ Successfully created betting lines for \(gameID)")
                return bettingLines
                
            } else {
                // Handle nested sportsbook structure - use DraftKings as default
                print("🔄 Converting nested sportsbook structure to flat structure")
                
                let preferredSportsbooks = ["draftkings", "fanduel", "betmgm"] // Priority order
                var selectedSportsbook: [String: Any]?
                
                // Find the first available sportsbook
                for sportsbook in preferredSportsbooks {
                    if let sportsbookData = data[sportsbook] as? [String: Any] {
                        selectedSportsbook = sportsbookData
                        print("📱 Using \(sportsbook) data")
                        break
                    }
                }
                
                // If no preferred sportsbook found, use the first available
                if selectedSportsbook == nil {
                    for (key, value) in data {
                        if key != "gameID", let sportsbookData = value as? [String: Any] {
                            selectedSportsbook = sportsbookData
                            print("📱 Using \(key) data as fallback")
                            break
                        }
                    }
                }
                
                guard let sportsbookData = selectedSportsbook,
                      let moneyline = sportsbookData["moneyline"] as? [String: Double],
                      let spread = sportsbookData["spread"] as? [String: Double],
                      let total = sportsbookData["total"] as? [String: Double] else {
                    print("❌ Could not extract betting lines from any sportsbook")
                    return nil
                }
                
                print("💰 Moneyline: \(moneyline)")
                print("📊 Spread: \(spread)")
                print("🎯 Total: \(total)")
                
                let bettingLines = BettingLines(
                    id: document.documentID,
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                
                print("✅ Successfully created betting lines for \(gameID)")
                return bettingLines
            }
            
        } catch {
            print("❌ Error fetching betting lines for \(gameID): \(error)")
            throw error
        }
    }
    
    // MARK: - Predictions
    func fetchPredictionInfo(for gameID: String) async throws -> PredictionInfo? {
        print("🔍 FirebaseService: Fetching prediction for game: \(gameID)")
        
        do {
            let document = try await db.collection("predictions").document(gameID).getDocument()
            
            guard document.exists, let data = document.data() else {
                print("❌ No prediction data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Prediction data keys: \(data.keys.sorted())")
            
            let confidence = data["confidence"] as? Double ?? 0.0
            let recommendedBet = data["recommendedBet"] as? String
            let analysis = data["analysis"] as? String
            
            print("🧠 Confidence: \(confidence)%")
            print("🎯 Recommended bet: \(recommendedBet ?? "none")")
            print("📝 Analysis: \(analysis ?? "none")")
            
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
    
    // MARK: - Bet Slips (Updated section of FirebaseService.swift)
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
    // MARK: - Fetch All Betting Lines for Multiple Sportsbooks
    private func fetchAllBettingLines(for gameID: String) async throws -> AllSportsbookLines? {
        print("🔍 FirebaseService: Fetching all betting lines for game: \(gameID)")
        
        do {
            let document = try await db.collection("bettingLines").document(gameID).getDocument()
            
            guard document.exists, let data = document.data() else {
                print("❌ No betting lines data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Betting lines data keys: \(data.keys.sorted())")
            
            // Parse each sportsbook's betting lines
            var draftkingsLines: BettingLines?
            var betmgmLines: BettingLines?
            var fanduelLines: BettingLines?
            var caesarsLines: BettingLines?
            var pointsbetLines: BettingLines?
            var barstoolLines: BettingLines?
            
            // DraftKings
            if let dkData = data["draftkings"] as? [String: Any],
               let moneyline = dkData["moneyline"] as? [String: Double],
               let spread = dkData["spread"] as? [String: Double],
               let total = dkData["total"] as? [String: Double] {
                draftkingsLines = BettingLines(
                    id: "\(gameID)_draftkings",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed DraftKings lines")
            }
            
            // BetMGM
            if let mgmData = data["betmgm"] as? [String: Any],
               let moneyline = mgmData["moneyline"] as? [String: Double],
               let spread = mgmData["spread"] as? [String: Double],
               let total = mgmData["total"] as? [String: Double] {
                betmgmLines = BettingLines(
                    id: "\(gameID)_betmgm",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed BetMGM lines")
            }
            
            // FanDuel
            if let fdData = data["fanduel"] as? [String: Any],
               let moneyline = fdData["moneyline"] as? [String: Double],
               let spread = fdData["spread"] as? [String: Double],
               let total = fdData["total"] as? [String: Double] {
                fanduelLines = BettingLines(
                    id: "\(gameID)_fanduel",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed FanDuel lines")
            }
            
            // Caesars
            if let caesarsData = data["caesars"] as? [String: Any],
               let moneyline = caesarsData["moneyline"] as? [String: Double],
               let spread = caesarsData["spread"] as? [String: Double],
               let total = caesarsData["total"] as? [String: Double] {
                caesarsLines = BettingLines(
                    id: "\(gameID)_caesars",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed Caesars lines")
            }
            
            // PointsBet
            if let pbData = data["pointsbet"] as? [String: Any],
               let moneyline = pbData["moneyline"] as? [String: Double],
               let spread = pbData["spread"] as? [String: Double],
               let total = pbData["total"] as? [String: Double] {
                pointsbetLines = BettingLines(
                    id: "\(gameID)_pointsbet",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed PointsBet lines")
            }
            
            // Barstool
            if let bsData = data["barstool"] as? [String: Any],
               let moneyline = bsData["moneyline"] as? [String: Double],
               let spread = bsData["spread"] as? [String: Double],
               let total = bsData["total"] as? [String: Double] {
                barstoolLines = BettingLines(
                    id: "\(gameID)_barstool",
                    gameID: gameID,
                    moneyline: moneyline,
                    spread: spread,
                    total: total
                )
                print("✅ Parsed Barstool lines")
            }
            
            let allLines = AllSportsbookLines(
                draftkings: draftkingsLines,
                betmgm: betmgmLines,
                fanduel: fanduelLines,
                caesars: caesarsLines,
                pointsbet: pointsbetLines,
                barstool: barstoolLines
            )
            
            print("✅ Successfully created all sportsbook lines for \(gameID)")
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
