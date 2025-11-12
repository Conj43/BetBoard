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
    
    // Helper function to get the current date as string
    private func getCurrentDateString() -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        return dateFormatter.string(from: Date())
    }
    
    // MARK: - Games
    func fetchGames() async throws -> [Game] {
        print("🔍 FirebaseService: Attempting to fetch games from new path...")
        
        let currentDateStr = getCurrentDateString()
        
        // Use the new path structure as provided
        let gamesRef = db.collection("games").document(currentDateStr).collection("games")
        let snapshot = try await gamesRef.getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) game documents")
        
        let games = snapshot.documents.compactMap { document -> Game? in
            print("📄 Processing game document: \(document.documentID)")
            let data = document.data()
            print("📊 Game data keys: \(data.keys.sorted())")
            
            guard let homeTeam = data["home_team"] as? String,
                  let awayTeam = data["away_team"] as? String,
                  let dateString = data["date"] as? String,
                  let neutralSite = data["neutral_site"] as? Bool,
                  let gameID = data["game_id"] as? String else {
                print("❌ Missing required fields in game \(document.documentID)")
                print("   home_team: \(data["home_team"] ?? "nil")")
                print("   away_team: \(data["away_team"] ?? "nil")")
                print("   date: \(data["date"] ?? "nil")")
                print("   neutral_site: \(data["neutral_site"] ?? "nil")")
                print("   game_id: \(data["game_id"] ?? "nil")")
                return nil
            }
            
            // Parse date string to Date object
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd" // Format matches "2025-11-09"
            guard let gameDate = dateFormatter.date(from: dateString) else {
                print("❌ Failed to parse date: \(dateString)")
                return nil
            }
            
            // Get additional fields that might be present
            let homeConference = data["home_conf"] as? String
            let awayConference = data["away_conf"] as? String
            let torvikHomeRank = data["torvik_home_rank"] as? Int
            let torvikAwayRank = data["torvik_away_rank"] as? Int
            let tipoffTime = data["tipoff_time"] as? String
            let season = data["season"] as? String
            let predictedWinner = data["predicted_winner"] as? String
            
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
            
            let combinedDateTime = combineDateAndTipoffTime(date: gameDate, tipoffTime: tipoffTime)
            
            return Game(
                id: gameID,
                homeTeam: homeTeam,
                awayTeam: awayTeam,
                date: combinedDateTime,
                status: status,
                neutralSite: neutralSite,
                homeConference: homeConference,
                awayConference: awayConference,
                torvikHomeRank: torvikHomeRank,
                torvikAwayRank: torvikAwayRank,
                tipoffTime: tipoffTime,
                season: season,
                predictedWinner: predictedWinner
            )
        }
        
        print("✅ Successfully processed \(games.count) games")
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
    
    // MARK: - Fetch All Betting Lines for a Game
    func fetchAllBettingLines(for gameID: String) async throws -> AllSportsbookLines? {
        print("🔍 FirebaseService: Fetching all betting lines for game: \(gameID)")
        
        // Extract date from gameID (format: "2025-11-09_missouri_virginia-military-institute")
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard gameIDComponents.count >= 2 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        let dateStr = gameIDComponents[0]
        
        do {
            // First, check if the game document exists
            let gameDoc = try await db.collection("games")
                                     .document(dateStr)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            // Access the sportsbookOdds subcollection for the game
            let sportsbookCollection = db.collection("games")
                                        .document(dateStr)
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
            var betonlineagLines: BettingLines?
            var betriversLines: BettingLines?
            var bovadaLines: BettingLines?
            var lowvigLines: BettingLines?
            
            // Get game data for team names
            let gameData = gameDoc.data() ?? [:]
            let homeTeamName = gameData["home_team"] as? String ?? "Home"
            let awayTeamName = gameData["away_team"] as? String ?? "Away"
            
            // Process each sportsbook document
            for sportsbookDoc in sportsbookSnapshot.documents {
                let sportsbookName = sportsbookDoc.documentID.lowercased()
                let sportsbookData = sportsbookDoc.data()
                
                print("🏢 Processing sportsbook: \(sportsbookName)")
                print("💵 Data contains moneyline? \(sportsbookData["moneyline"] != nil)")
                
                // Process moneyline data
                var moneylineMap: [String: Double] = [:]
                if let moneylineData = sportsbookData["moneyline"] as? [String: Any] {
                    print("💰 Moneyline data: \(moneylineData)")
                    
                    // Process away team moneyline
                    if let awayPrice = moneylineData["away"] as? Double {
                        // Simple Double format
                        moneylineMap[awayTeamName] = awayPrice
                        print("✓ Added away moneyline: \(awayTeamName) = \(awayPrice)")
                    } else if let awayDict = moneylineData["away"] as? [String: Any],
                              let awayPrice = awayDict["price"] as? Double {
                        // Nested dictionary format
                        moneylineMap[awayTeamName] = awayPrice
                        print("✓ Added away moneyline from dict: \(awayTeamName) = \(awayPrice)")
                    }
                    
                    // Process home team moneyline
                    if let homePrice = moneylineData["home"] as? Double {
                        // Simple Double format
                        moneylineMap[homeTeamName] = homePrice
                        print("✓ Added home moneyline: \(homeTeamName) = \(homePrice)")
                    } else if let homeDict = moneylineData["home"] as? [String: Any],
                              let homePrice = homeDict["price"] as? Double {
                        // Nested dictionary format
                        moneylineMap[homeTeamName] = homePrice
                        print("✓ Added home moneyline from dict: \(homeTeamName) = \(homePrice)")
                    }
                }
                
                // Verify moneyline data
                if !moneylineMap.isEmpty {
                    print("✅ Successfully processed moneyline data: \(moneylineMap)")
                } else {
                    print("⚠️ No moneyline data found or processed")
                }
                
                // Process spread data - new format
                var spreadMap: [String: Double] = [:]
                if let spreadData = sportsbookData["spread"] as? [String: Any] {
                    // Process away team spread
                    if let awaySpread = spreadData["away"] as? [String: Any],
                       let line = awaySpread["line"] as? Double,
                       let price = awaySpread["price"] as? Double {
                        // Format key as "TEAM +/-LINE"
                        let formattedKey = "\(awayTeamName) +\(abs(line))"
                        spreadMap[formattedKey] = price
                    }
                    
                    // Process home team spread
                    if let homeSpread = spreadData["home"] as? [String: Any],
                       let line = homeSpread["line"] as? Double,
                       let price = homeSpread["price"] as? Double {
                        // Format key as "TEAM +/-LINE"
                        let linePrefix = line >= 0 ? "+" : ""
                        let formattedKey = "\(homeTeamName) \(linePrefix)\(line)"
                        spreadMap[formattedKey] = price
                    }
                }
                
                // Process total data - new format
                var totalMap: [String: Double] = [:]
                if let totalData = sportsbookData["total"] as? [String: Any] {
                    // For total, we might have over and under
                    if let overTotal = totalData["over"] as? [String: Any],
                       let line = overTotal["line"] as? Double,
                       let price = overTotal["price"] as? Double {
                        let formattedKey = "Over \(line)"
                        totalMap[formattedKey] = price
                    }
                    
                    if let underTotal = totalData["under"] as? [String: Any],
                       let line = underTotal["line"] as? Double,
                       let price = underTotal["price"] as? Double {
                        let formattedKey = "Under \(line)"
                        totalMap[formattedKey] = price
                    }
                }
                
                // Create BettingLines object with moneyline
                let bettingLines = BettingLines.create(
                    id: "\(gameID)_\(sportsbookName)",
                    gameID: gameID,
                    moneyline: moneylineMap,
                    spread: spreadMap,
                    total: totalMap
                )
                
                // Assign to appropriate sportsbook variable
                switch sportsbookName {
                case "draftkings":
                    draftkingsLines = bettingLines
                case "betmgm":
                    betmgmLines = bettingLines
                case "fanduel":
                    fanduelLines = bettingLines
                case "caesars":
                    caesarsLines = bettingLines
                case "pointsbet":
                    pointsbetLines = bettingLines
                case "barstool":
                    barstoolLines = bettingLines
                case "betonlineag":
                    betonlineagLines = bettingLines
                case "betrivers":
                    betriversLines = bettingLines
                case "bovada":
                    bovadaLines = bettingLines
                case "lowvig":
                    lowvigLines = bettingLines
                default:
                    print("⚠️ Unknown sportsbook: \(sportsbookName)")
                    break
                }
            }
            
            // Create and return AllSportsbookLines object
            return AllSportsbookLines(
                draftkings: draftkingsLines,
                betmgm: betmgmLines,
                fanduel: fanduelLines,
                caesars: caesarsLines,
                pointsbet: pointsbetLines,
                barstool: barstoolLines,
                betonlineag: betonlineagLines,
                betrivers: betriversLines,
                bovada: bovadaLines,
                lowvig: lowvigLines
            )
            
        } catch {
            print("❌ Error fetching betting lines: \(error)")
            return nil
        }
    }
    
    // MARK: - Fetch Prediction Info
    func fetchPredictionInfo(for gameID: String) async throws -> PredictionInfo? {
        print("🔍 FirebaseService: Fetching prediction info for game: \(gameID)")
        
        // Extract date from gameID
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard gameIDComponents.count >= 2 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        let dateStr = gameIDComponents[0]
        
        do {
            // Get the game document
            let gameDoc = try await db.collection("games")
                                     .document(dateStr)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            // Extract prediction data directly from the game document
            let data = gameDoc.data() ?? [:]
            
            // Extract spread data
            let spreadData = data["spread"] as? [String: Any]
            
            // Extract total data
            let totalData = data["total"] as? [String: Any]
            
            // No prediction data available
            if spreadData == nil && totalData == nil {
                print("⚠️ No prediction data available for game: \(gameID)")
                return nil
            }
            
            // Create prediction info from the new data structure
            let predictionInfo = PredictionInfo.fromFirebaseData(
                spreadData: spreadData,
                totalData: totalData,
                analysis: nil // No analysis field in the current data structure
            )
            
            if predictionInfo != nil {
                print("✅ Successfully created prediction info")
                print("📊 Spread: \(predictionInfo?.spreadBet ?? "none") (\(predictionInfo?.spreadConfidence ?? 0)%)")
                print("📈 Total: \(predictionInfo?.totalBet ?? "none") (\(predictionInfo?.totalConfidence ?? 0)%)")
            } else {
                print("⚠️ Failed to create prediction info from data")
            }
            
            return predictionInfo
            
        } catch {
            print("❌ Error fetching prediction for \(gameID): \(error)")
            throw error
        }
    }
    
    // MARK: - Fetch Bet Slips
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
                teamLookup[team.name] = team  // Also add by full name for matching
                teamLookup[team.id] = team    // Also add by ID in case it's used
                print("🔗 Added team to lookup: \(team.shortName) -> \(team.name)")
            }
            
            var betSlips: [BetSlip] = []
            
            print("🎮 Processing \(games.count) games...")
            for game in games {
                print("🎮 Processing game: \(game.homeTeam) vs \(game.awayTeam) (ID: \(game.id))")
                
                // Try to find teams by exact match first, then try partial match
                var homeTeamObj = teamLookup[game.homeTeam]
                var awayTeamObj = teamLookup[game.awayTeam]

                // If direct lookup failed, try normalized formats (uppercase/lowercase)
                if homeTeamObj == nil {
                    // Try uppercase
                    homeTeamObj = teamLookup[game.homeTeam.uppercased()]
                    
                    // Try lowercase if still nil
                    if homeTeamObj == nil {
                        homeTeamObj = teamLookup[game.homeTeam.lowercased()]
                    }
                }

                if awayTeamObj == nil {
                    // Try uppercase
                    awayTeamObj = teamLookup[game.awayTeam.uppercased()]
                    
                    // Try lowercase if still nil
                    if awayTeamObj == nil {
                        awayTeamObj = teamLookup[game.awayTeam.lowercased()]
                    }
                }

                // No partial matching at all - if we can't find it, skip or use a placeholder
                if homeTeamObj == nil || awayTeamObj == nil {
                    print("⚠️ Could not find exact match for teams in game: \(game.homeTeam) vs \(game.awayTeam)")
                    // Skip this game or handle the missing team case as needed
                    continue
                }
                
                guard let homeTeam = homeTeamObj, let awayTeam = awayTeamObj else {
                    print("❌ Could not find teams for game: \(game.homeTeam) vs \(game.awayTeam)")
                    print("   Available teams: \(teamLookup.keys.sorted().prefix(10))")
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
                    allBettingLines.betonlineag ??
                    allBettingLines.betrivers ??
                    allBettingLines.bovada ??
                    allBettingLines.lowvig ??
                    BettingLines.create(id: game.id, gameID: game.id, moneyline: [:], spread: [:], total: [:])
                    
                    let betSlip = BetSlip(
                        id: game.id,
                        gameID: game.id,
                        sportsbook: .draftkings, // Default sportsbook
                        homeTeam: homeTeam,
                        awayTeam: awayTeam,
                        gameTime: game.date,
                        tipoffTimeString: game.tipoffTime,
                        bettingLines: defaultBettingLines,
                        allBettingLines: allBettingLines,
                        predictionInfo: predictionInfo,
                        neutralSite: game.neutralSite,
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
    
    // Helper function to combine date and tipoff time into a complete date-time object
    func combineDateAndTipoffTime(date: Date, tipoffTime: String?) -> Date {
        // If no tipoff time is provided, return the original date
        guard let tipoffTimeString = tipoffTime else {
            return date
        }
        
        // Create a calendar for date manipulation
        let calendar = Calendar.current
        
        // Extract components from the original date
        let dateComponents = calendar.dateComponents([.year, .month, .day], from: date)
        
        // Parse the tipoff time string (e.g., "6:00 PM CT")
        // First, try to extract just the time part (remove timezone)
        let timeComponents = tipoffTimeString.components(separatedBy: " ")
        guard timeComponents.count >= 2 else {
            // If the format is not as expected, return the original date
            return date
        }
        
        // Combine the time and AM/PM
        let timeString = "\(timeComponents[0]) \(timeComponents[1])"
        
        // Parse the time
        let timeFormatter = DateFormatter()
        timeFormatter.dateFormat = "h:mm a"
        
        guard let parsedTime = timeFormatter.date(from: timeString) else {
            // If time parsing fails, return the original date
            return date
        }
        
        // Extract hour and minute from the parsed time
        let timeComponents2 = calendar.dateComponents([.hour, .minute], from: parsedTime)
        
        // Create updated date components with both date and time
        var updatedComponents = dateComponents
        updatedComponents.hour = timeComponents2.hour
        updatedComponents.minute = timeComponents2.minute
        
        // Create the final date
        return calendar.date(from: updatedComponents) ?? date
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
        if allLines.betonlineag != nil { sportsbooks.append("BetOnlineAG") }
        if allLines.betrivers != nil { sportsbooks.append("BetRivers") }
        if allLines.bovada != nil { sportsbooks.append("Bovada") }
        if allLines.lowvig != nil { sportsbooks.append("LowVig") }
        return sportsbooks
    }
}
