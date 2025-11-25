//
//  TeamDetailViewModel.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/25/25.
//  Optimized to reduce Firebase calls and improve performance
//

import Foundation
import Combine
import FirebaseFirestore

// Lightweight game model without betting lines
struct TeamGame: Identifiable {
    let id: String
    let gameID: String
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let tipoffTimeString: String?
    let neutralSite: Bool
    let homeConference: String?
    let awayConference: String?
    let homeRanking: Int?
    let awayRanking: Int?
    let gameResult: GameResult?
    
    var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd - h:mm a"
        return formatter.string(from: gameTime)
    }
}

@MainActor
class TeamDetailViewModel: ObservableObject {
    @Published var upcomingGames: [TeamGame] = []
    @Published var completedGames: [TeamGame] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let team: Team
    private let firebaseService = FirebaseService()
    
    // Cache to store games by team ID
    private static var gamesCache: [String: (upcoming: [TeamGame], completed: [TeamGame], timestamp: Date)] = [:]
    private static let cacheExpiry: TimeInterval = 300 // 5 minutes
    
    init(team: Team) {
        self.team = team
    }
    
    func loadGames() async {
        print("📊 TeamDetailViewModel: Loading games for \(team.shortName)...")
        
        // Check cache first
        if let cached = Self.gamesCache[team.id],
           Date().timeIntervalSince(cached.timestamp) < Self.cacheExpiry {
            print("✅ Using cached games for \(team.shortName)")
            self.upcomingGames = cached.upcoming
            self.completedGames = cached.completed
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let calendar = Calendar.current
            let today = Date()
            let pastDate = calendar.date(byAdding: .day, value: -30, to: today) ?? today
            let futureDate = calendar.date(byAdding: .day, value: 30, to: today) ?? today
            
            var dates: [Date] = []
            var currentDate = pastDate
            while currentDate <= futureDate {
                dates.append(currentDate)
                currentDate = calendar.date(byAdding: .day, value: 1, to: currentDate) ?? currentDate
            }
            
            // Fetch games in parallel without betting lines
            let allGames = await withTaskGroup(of: [TeamGame].self) { group in
                for date in dates {
                    group.addTask {
                        await self.fetchLightweightGames(for: date)
                    }
                }
                
                var results: [TeamGame] = []
                for await games in group {
                    results.append(contentsOf: games)
                }
                return results
            }
            
            print("✅ Fetched \(allGames.count) total games")
            
            // Filter games for this team
            let teamGames = allGames.filter { game in
                game.homeTeam.id == team.id ||
                game.homeTeam.shortName.uppercased() == team.shortName.uppercased() ||
                game.awayTeam.id == team.id ||
                game.awayTeam.shortName.uppercased() == team.shortName.uppercased()
            }
            
            print("🎯 Found \(teamGames.count) games for \(team.shortName)")
            
            // Separate into upcoming and completed
            let now = Date()
            let upcoming = teamGames.filter { $0.gameTime >= now }
                .sorted { $0.gameTime < $1.gameTime }
            let completed = teamGames.filter { $0.gameTime < now }
                .sorted { $0.gameTime > $1.gameTime }
            
            // Cache the results
            Self.gamesCache[team.id] = (upcoming, completed, Date())
            
            await MainActor.run {
                self.upcomingGames = upcoming
                self.completedGames = completed
                self.isLoading = false
            }
            
            print("📅 Upcoming: \(upcoming.count), Completed: \(completed.count)")
            
        }
    }
    
    // Fetch lightweight games without betting lines
    private func fetchLightweightGames(for date: Date) async -> [TeamGame] {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let dateStr = dateFormatter.string(from: date)
        
        do {
            let db = Firestore.firestore()
            let gamesSnapshot = try await db.collection("games")
                .document(dateStr)
                .collection("games")
                .getDocuments()
            
            let teams = try await firebaseService.fetchTeams()
            var teamLookup: [String: Team] = [:]
            for team in teams {
                teamLookup[team.shortName.uppercased()] = team
                teamLookup[team.name.uppercased()] = team
                teamLookup[team.id.uppercased()] = team
            }
            
            var games: [TeamGame] = []
            
            for gameDoc in gamesSnapshot.documents {
                let data = gameDoc.data()
                
                guard let homeTeamName = data["home_team"] as? String,
                      let awayTeamName = data["away_team"] as? String,
                      let gameID = data["game_id"] as? String,
                      let neutralSite = data["neutral_site"] as? Bool else {
                    continue
                }
                
                let homeTeam = findTeam(homeTeamName, in: teamLookup) ?? createPlaceholderTeam(name: homeTeamName, data: data, isHome: true)
                let awayTeam = findTeam(awayTeamName, in: teamLookup) ?? createPlaceholderTeam(name: awayTeamName, data: data, isHome: false)
                
                let tipoffTime = data["tipoff_time"] as? String
                let gameTime = combineDateAndTipoffTime(date: date, tipoffTime: tipoffTime)
                
                // Check for game result if completed
                var gameResult: GameResult?
                if gameTime < Date() {
                    gameResult = await fetchGameResult(gameID: gameID, dateStr: dateStr, homeTeam: homeTeam.shortName, awayTeam: awayTeam.shortName)
                }
                
                let game = TeamGame(
                    id: gameID,
                    gameID: gameID,
                    homeTeam: homeTeam,
                    awayTeam: awayTeam,
                    gameTime: gameTime,
                    tipoffTimeString: tipoffTime,
                    neutralSite: neutralSite,
                    homeConference: data["home_conf"] as? String,
                    awayConference: data["away_conf"] as? String,
                    homeRanking: data["torvik_home_rank"] as? Int,
                    awayRanking: data["torvik_away_rank"] as? Int,
                    gameResult: gameResult
                )
                
                games.append(game)
            }
            
            return games
            
        } catch {
            print("⚠️ Error fetching games for \(dateStr): \(error)")
            return []
        }
    }
    
    private func fetchGameResult(gameID: String, dateStr: String, homeTeam: String, awayTeam: String) async -> GameResult? {
        do {
            let db = Firestore.firestore()
            let resultsDoc = try await db.collection("games")
                .document(dateStr)
                .collection("games")
                .document(gameID)
                .collection("game_results")
                .document("odds_api")
                .getDocument()
            
            if resultsDoc.exists,
               let resultData = resultsDoc.data(),
               let completed = resultData["completed"] as? Bool,
               completed,
               let homeScore = resultData["home_score"] as? Int,
               let awayScore = resultData["away_score"] as? Int {
                
                return GameResult(
                    homeScore: homeScore,
                    awayScore: awayScore,
                    homeTeam: homeTeam,
                    awayTeam: awayTeam
                )
            }
        } catch {
            print("❌ Error fetching game result for \(gameID): \(error)")
        }
        
        return nil
    }
    
    private func findTeam(_ teamName: String, in lookup: [String: Team]) -> Team? {
        return lookup[teamName.uppercased()]
    }
    
    private func createPlaceholderTeam(name: String, data: [String: Any], isHome: Bool) -> Team {
        let conference = isHome ? (data["home_conf"] as? String) : (data["away_conf"] as? String)
        let ranking = isHome ? (data["torvik_home_rank"] as? Int) : (data["torvik_away_rank"] as? Int)
        
        return Team(
            id: name.replacingOccurrences(of: " ", with: "_"),
            name: name,
            shortName: name,
            logoURL: "https://via.placeholder.com/150",
            record: TeamRecord(wins: 0, losses: 0),
            conference: conference ?? "Unknown",
            ranking: ranking,
            colorHex: nil
        )
    }
    
    private func combineDateAndTipoffTime(date: Date, tipoffTime: String?) -> Date {
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
    
    // Clear cache when needed
    static func clearCache() {
        gamesCache.removeAll()
    }
}

// MARK: - Team Game Row ViewModel (Simplified)
@MainActor
class TeamGameRowViewModel: ObservableObject {
    @Published var gameResult: GameResult?
    @Published var isCompleted = false
    
    private let game: TeamGame
    
    init(game: TeamGame) {
        self.game = game
        self.isCompleted = game.gameTime < Date()
        self.gameResult = game.gameResult
    }
}
