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
    
    // Add caching
    private var cachedTeams: [Team]?
    private var teamsCacheDate: Date?
    private let teamsCacheExpiry: TimeInterval = 86400 // 24 hours
    
    // Helper function to get the current date as string
    private func getCurrentDateString() -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        return dateFormatter.string(from: Date())
    }
    
    // MARK: - Games
    func fetchGames(for date: Date = Date()) async throws -> [Game] {
        print("🔍 FirebaseService: Attempting to fetch games for date...")
        
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let currentDateStr = dateFormatter.string(from: date)
        
        print("🔍 Querying path: games/\(currentDateStr)/games")
        
        let gamesRef = db.collection("games").document(currentDateStr).collection("games")
        let snapshot = try await gamesRef.getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) game documents for \(currentDateStr)")
        
        let games = snapshot.documents.compactMap { document -> Game? in
            let data = document.data()
            
            guard let homeTeam = data["home_team"] as? String,
                  let awayTeam = data["away_team"] as? String,
                  let dateString = data["date"] as? String,
                  let neutralSite = data["neutral_site"] as? Bool,
                  let gameID = data["game_id"] as? String else {
                print("❌ Missing required fields in game \(document.documentID)")
                return nil
            }
            
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            guard let gameDate = dateFormatter.date(from: dateString) else {
                print("❌ Failed to parse date: \(dateString)")
                return nil
            }
            
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
            
            // Extract prediction info from game data
            let spreadData = data["spread"] as? [String: Any]
            let totalData = data["total"] as? [String: Any]

            // Get p_win values from moneyline object
            let moneylineData = data["moneyline"] as? [String: Any]
            let pWinHome = moneylineData?["p_win_home"] as? Double
            let pWinAway = moneylineData?["p_win_away"] as? Double



            let predictionInfo = PredictionInfo.fromFirebaseData(
                spreadData: spreadData,
                totalData: totalData,
                analysis: nil,
                pWinHome: pWinHome,
                pWinAway: pWinAway
            )
            
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
                predictedWinner: predictedWinner,
                predictionInfo: predictionInfo
            )
        }
        
        print("✅ Successfully processed \(games.count) games")
        return games
    }
    
    // MARK: - Teams (with caching)
    func fetchTeams() async throws -> [Team] {
        // Check cache
        if let cached = cachedTeams,
           let cacheDate = teamsCacheDate,
           Date().timeIntervalSince(cacheDate) < teamsCacheExpiry {
            print("✅ Using cached teams (\(cached.count))")
            return cached
        }
        
        print("🔍 FirebaseService: Fetching teams from Firebase...")
        
        let snapshot = try await db.collection("teams").getDocuments()
        print("✅ FirebaseService: Successfully fetched \(snapshot.documents.count) team documents")
        
        let teams = snapshot.documents.compactMap { document -> Team? in
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
            
            return Team(
                id: document.documentID,
                name: name,
                shortName: shortName,
                logoURL: logoURL,
                record: TeamRecord(wins: wins, losses: losses),
                conference: conference,
                ranking: data["ranking"] as? Int,
                colorHex: data["colorHex"] as? String
            )
        }
        
        // Cache the results
        self.cachedTeams = teams
        self.teamsCacheDate = Date()
        
        print("🎯 FirebaseService: Final teams count: \(teams.count) (cached)")
        return teams
    }
    
    // MARK: - Fetch All Betting Lines for a Game
    func fetchAllBettingLines(for gameID: String) async throws -> AllSportsbookLines? {
        print("🔍 FirebaseService: Fetching all betting lines for game: \(gameID)")
        
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard gameIDComponents.count >= 2 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        let dateStr = gameIDComponents[0]
        
        do {
            let gameDoc = try await db.collection("games")
                                     .document(dateStr)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            let sportsbookCollection = db.collection("games")
                                        .document(dateStr)
                                        .collection("games")
                                        .document(gameID)
                                        .collection("sportsbookOdds")
            
            let sportsbookSnapshot = try await sportsbookCollection.getDocuments()
            
            if sportsbookSnapshot.documents.isEmpty {
                print("❌ No sportsbook data found for game: \(gameID)")
                return nil
            }
            
            print("📊 Found \(sportsbookSnapshot.documents.count) sportsbooks for game: \(gameID)")
            
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
            
            let gameData = gameDoc.data() ?? [:]
            let homeTeamName = gameData["home_team"] as? String ?? "Home"
            let awayTeamName = gameData["away_team"] as? String ?? "Away"
            
            for sportsbookDoc in sportsbookSnapshot.documents {
                let sportsbookName = sportsbookDoc.documentID.lowercased()
                let sportsbookData = sportsbookDoc.data()
                
                var moneylineMap: [String: Double] = [:]
                if let moneylineData = sportsbookData["moneyline"] as? [String: Any] {
                    if let awayPrice = moneylineData["away"] as? Double {
                        moneylineMap[awayTeamName] = awayPrice
                    } else if let awayDict = moneylineData["away"] as? [String: Any],
                              let awayPrice = awayDict["price"] as? Double {
                        moneylineMap[awayTeamName] = awayPrice
                    }
                    
                    if let homePrice = moneylineData["home"] as? Double {
                        moneylineMap[homeTeamName] = homePrice
                    } else if let homeDict = moneylineData["home"] as? [String: Any],
                              let homePrice = homeDict["price"] as? Double {
                        moneylineMap[homeTeamName] = homePrice
                    }
                }
                
                var spreadMap: [String: Double] = [:]
                if let spreadData = sportsbookData["spread"] as? [String: Any] {
                    if let awaySpread = spreadData["away"] as? [String: Any],
                       let line = awaySpread["line"] as? Double,
                       let price = awaySpread["price"] as? Double {
                        
                        let formattedLine = line > 0
                            ? "+\(String(format: "%.1f", line))"
                            : "\(String(format: "%.1f", line))"
                        
                        let formattedKey = "\(awayTeamName) \(formattedLine)"
                        spreadMap[formattedKey] = price
                    }

                    if let homeSpread = spreadData["home"] as? [String: Any],
                       let line = homeSpread["line"] as? Double,
                       let price = homeSpread["price"] as? Double {
                        
                        let formattedLine = line > 0
                            ? "+\(String(format: "%.1f", line))"
                            : "\(String(format: "%.1f", line))"
                        
                        let formattedKey = "\(homeTeamName) \(formattedLine)"
                        spreadMap[formattedKey] = price
                    }
                }
                
                var totalMap: [String: Double] = [:]
                if let totalData = sportsbookData["total"] as? [String: Any] {
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
                
                let bettingLines = BettingLines.create(
                    id: "\(gameID)_\(sportsbookName)",
                    gameID: gameID,
                    moneyline: moneylineMap,
                    spread: spreadMap,
                    total: totalMap
                )
                
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
                    break
                }
            }
            
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
    
    // MARK: - Fetch Bet Slips (Optimized with Parallel Queries)
    func fetchBetSlips(for date: Date = Date()) async throws -> [BetSlip] {
        print("🔍 FirebaseService: Starting to fetch bet slips for date: \(date)...")
        
        do {
            let games = try await fetchGames(for: date)
            let teams = try await fetchTeams()
            
            print("📊 Fetched \(games.count) games and \(teams.count) teams")
            
            // Create team lookup dictionary
            var teamLookup: [String: Team] = [:]
            for team in teams {
                teamLookup[team.shortName.uppercased()] = team
                teamLookup[team.name.uppercased()] = team
                teamLookup[team.id.uppercased()] = team
            }
            
            print("🔗 Team lookup created with \(teamLookup.count) entries")
            
            // Fetch all betting lines in parallel
            print("⚡️ Fetching betting lines in parallel...")
            let bettingLinesResults = await withTaskGroup(of: (String, AllSportsbookLines?).self) { group in
                for game in games {
                    group.addTask {
                        let lines = try? await self.fetchAllBettingLines(for: game.id)
                        return (game.id, lines)
                    }
                }
                
                var results: [String: AllSportsbookLines] = [:]
                for await (gameID, lines) in group {
                    if let lines = lines {
                        results[gameID] = lines
                    }
                }
                return results
            }
            
            print("✅ Fetched betting lines for \(bettingLinesResults.count) games")
            
            var betSlips: [BetSlip] = []
            
            print("🎮 Processing \(games.count) games...")
            for game in games {
                // Find teams
                let homeTeam: Team
                if let found = findTeam(game.homeTeam, in: teamLookup) {
                    homeTeam = found
                } else {
                    print("⚠️ Creating placeholder for home team: \(game.homeTeam)")
                    homeTeam = Team(
                        id: game.homeTeam.replacingOccurrences(of: " ", with: "_"),
                        name: game.homeTeam,
                        shortName: game.homeTeam,
                        logoURL: "https://via.placeholder.com/150",
                        record: TeamRecord(wins: 0, losses: 0),
                        conference: game.homeConference ?? "Unknown",
                        ranking: game.torvikHomeRank,
                        colorHex: nil
                    )
                }
                
                let awayTeam: Team
                if let found = findTeam(game.awayTeam, in: teamLookup) {
                    awayTeam = found
                } else {
                    print("⚠️ Creating placeholder for away team: \(game.awayTeam)")
                    awayTeam = Team(
                        id: game.awayTeam.replacingOccurrences(of: " ", with: "_"),
                        name: game.awayTeam,
                        shortName: game.awayTeam,
                        logoURL: "https://via.placeholder.com/150",
                        record: TeamRecord(wins: 0, losses: 0),
                        conference: game.awayConference ?? "Unknown",
                        ranking: game.torvikAwayRank,
                        colorHex: nil
                    )
                }
                
                // Get betting lines from parallel results
                if let allBettingLines = bettingLinesResults[game.id] {
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
                        sportsbook: .draftkings,
                        homeTeam: homeTeam,
                        awayTeam: awayTeam,
                        gameTime: game.date,
                        tipoffTimeString: game.tipoffTime,
                        bettingLines: defaultBettingLines,
                        allBettingLines: allBettingLines,
                        predictionInfo: game.predictionInfo, // Use from game data!
                        neutralSite: game.neutralSite,
                        homeConference: game.homeConference,
                        awayConference: game.awayConference,
                        homeRanking: game.torvikHomeRank,
                        awayRanking: game.torvikAwayRank
                    )
                    
                    betSlips.append(betSlip)
                }
            }
            
            print("🎯 FirebaseService: Final bet slips count: \(betSlips.count)")
            return betSlips
            
        } catch {
            print("❌ Error in fetchBetSlips: \(error)")
            throw error
        }
    }
    
    // MARK: - Helper: Find Team
    private func findTeam(_ teamName: String, in lookup: [String: Team]) -> Team? {
        if let team = lookup[teamName.uppercased()] {
            return team
        }
        return nil
    }
    
    // Helper function to combine date and tipoff time into a complete date-time object
    func combineDateAndTipoffTime(date: Date, tipoffTime: String?) -> Date {
        guard let tipoffTimeString = tipoffTime else {
            return date
        }
        
        let calendar = Calendar.current
        let dateComponents = calendar.dateComponents([.year, .month, .day], from: date)
        let timeComponents = tipoffTimeString.components(separatedBy: " ")
        guard timeComponents.count >= 2 else {
            return date
        }
        
        let timeString = "\(timeComponents[0]) \(timeComponents[1])"
        let timeFormatter = DateFormatter()
        timeFormatter.dateFormat = "h:mm a"
        
        guard let parsedTime = timeFormatter.date(from: timeString) else {
            return date
        }
        
        let timeComponents2 = calendar.dateComponents([.hour, .minute], from: parsedTime)
        var updatedComponents = dateComponents
        updatedComponents.hour = timeComponents2.hour
        updatedComponents.minute = timeComponents2.minute
        
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
                
                guard let gameID = data["gameID"] as? String,
                      let typeString = data["type"] as? String,
                      let type = BetType(rawValue: typeString),
                      let selection = data["selection"] as? String,
                      let odds = data["odds"] as? Double,
                      let amount = data["amount"] as? Double,
                      let resultString = data["result"] as? String,
                      let result = BetResult(rawValue: resultString),
                      let placedAtTimestamp = data["placedAt"] as? Timestamp else {
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
