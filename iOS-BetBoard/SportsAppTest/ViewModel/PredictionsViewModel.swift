//
//  PredictionsViewModel.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to handle moneyline bet types

import SwiftUI
import FirebaseAuth
import Firebase

// MARK: - View Mode
enum PredictionsViewMode {
    case allGames
    case recommended
}

enum ConferenceFilter: String, CaseIterable {
    case all = "All"
    case americaEast = "America East Conference"
    case americanAthletic = "American Athletic Conference"
    case atlantic10 = "Atlantic 10 Conference"
    case atlanticCoast = "Atlantic Coast Conference"
    case atlanticSun = "Atlantic Sun Conference"
    case big12 = "Big 12 Conference"
    case bigEast = "Big East Conference"
    case bigSky = "Big Sky Conference"
    case bigSouth = "Big South Conference"
    case bigTen = "Big Ten Conference"
    case bigWest = "Big West Conference"
    case colonialAthletic = "Colonial Athletic Association"
    case conferenceUSA = "Conference USA"
    case horizonLeague = "Horizon League"
    case ivyLeague = "Ivy League"
    case metroAtlantic = "Metro Atlantic Athletic Conference"
    case midAmerican = "Mid-American Conference"
    case midEastern = "Mid-Eastern Athletic Conference"
    case missouriValley = "Missouri Valley Conference"
    case mountainWest = "Mountain West Conference"
    case northeast = "Northeast Conference"
    case ohioValley = "Ohio Valley Conference"
    case pac12 = "Pac-12 Conference"
    case patriotLeague = "Patriot League"
    case southeastern = "Southeastern Conference"
    case southern = "Southern Conference"
    case southland = "Southland Conference"
    case southwesternAthletic = "Southwestern Athletic Conference"
    case summitLeague = "Summit League"
    case sunBelt = "Sun Belt Conference"
    case westCoast = "West Coast Conference"
    case westernAthletic = "Western Athletic Conference"
}

enum RankingFilter: String, CaseIterable {
    case all = "All"
    case top25 = "Top 25"
    case top50 = "Top 50"
}

// MARK: - PredictionsViewModel
@MainActor
class PredictionsViewModel: ObservableObject {
    // Data
    @Published var allGames: [PredictionGame] = []
    @Published var recommendedGames: [PredictionGame] = []
    @Published var filteredGames: [PredictionGame] = []
    
    // UI State
    @Published var viewMode: PredictionsViewMode = .recommended
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    
    // Filters
    @Published var selectedConference: ConferenceFilter = .all
    @Published var selectedRanking: RankingFilter = .all
    
    // Date selection and results
    @Published var selectedDate: Date = Date()
    @Published var gameResults: [String: GameResult] = [:]
    
    // Cache management
    private var lastLoadedDate: String?
    private var cacheKey: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: selectedDate)
    }
    private var betSlipsCache: [String: [BetSlip]] = [:]
    private var gameResultsCache: [String: [String: GameResult]] = [:]
    
    private let firebaseService = FirebaseService()
    private var gameStatusCache: [String: GameStatus] = [:]
    
    // Computed property for displayed games
    var filteredPredictions: [PredictionGame] {
        return filteredGames
    }
    

    func fetchGameResults(for date: Date) async throws -> [String: GameResult] {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateStr = formatter.string(from: date)
        
        print("🔍 Fetching game results for \(dateStr)...")
        
        // Get all games for this date
        let gamesSnapshot = try await Firestore.firestore()
            .collection("games")
            .document(dateStr)
            .collection("games")
            .getDocuments()
        
        var results: [String: GameResult] = [:]
        
        for gameDoc in gamesSnapshot.documents {
            let gameID = gameDoc.documentID
            let gameData = gameDoc.data()
            
            // Try to get game_results/odds_api subcollection document
            do {
                let resultsDoc = try await Firestore.firestore()
                    .collection("games")
                    .document(dateStr)
                    .collection("games")
                    .document(gameID)
                    .collection("game_results")
                    .document("odds_api")
                    .getDocument()
                
                // Check if results exist and game is completed
                if resultsDoc.exists,
                   let resultData = resultsDoc.data(),
                   let completed = resultData["completed"] as? Bool,
                   completed,
                   let homeScore = resultData["home_score"] as? Int,
                   let awayScore = resultData["away_score"] as? Int {
                    
                    // Get team names from the main game document
                    let homeTeam = gameData["home_team"] as? String ?? ""
                    let awayTeam = gameData["away_team"] as? String ?? ""
                    
                    results[gameID] = GameResult(
                        homeScore: homeScore,
                        awayScore: awayScore,
                        homeTeam: homeTeam,
                        awayTeam: awayTeam
                    )
                    
                    print("✅ Result: \(gameID) - \(awayTeam) \(awayScore) @ \(homeTeam) \(homeScore)")
                }
            } catch {
                // No results for this game yet, continue
                continue
            }
        }
        
        print("✅ Loaded \(results.count) game results for \(dateStr)")
        return results
    }
    
    func loadPredictions() async {
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            let cacheKey = dateFormatter.string(from: selectedDate)
            
            // Check if we already loaded this date
            if lastLoadedDate == cacheKey,
               let cachedBetSlips = betSlipsCache[cacheKey],
               !cachedBetSlips.isEmpty {
                print("✅ Using cached data for \(cacheKey)")
                
                // Use cached bet slips
                let allGames = cachedBetSlips.compactMap { createPredictionGameFromBetSlip($0) }
                    .sorted { $0.gameTime < $1.gameTime }
                
                self.allGames = allGames
                
                // Load recommended (always fetch top_picks as it might change)
                async let recommendedTask = loadRecommendedGames(from: cachedBetSlips)
                
                // Use cached game results if available
                if let cachedResults = gameResultsCache[cacheKey] {
                    self.gameResults = cachedResults
                    self.recommendedGames = try! await recommendedTask
                } else {
                    async let resultsTask = fetchGameResults(for: selectedDate)
                    let (results, recommendedGames) = try! await (resultsTask, recommendedTask)
                    self.gameResults = results
                    self.gameResultsCache[cacheKey] = results
                    self.recommendedGames = recommendedGames
                }
                
                applyFilters()
                return
            }
            
            print("🔄 Loading predictions for \(cacheKey)...")
            isLoading = true
            errorMessage = nil
            
            do {
                // ONLY FETCH BET SLIPS ONCE
                let betSlips = try await firebaseService.fetchBetSlips(for: selectedDate)
                
                // Cache bet slips
                betSlipsCache[cacheKey] = betSlips
                
                // Create all games from bet slips
                let allGames = betSlips.compactMap { createPredictionGameFromBetSlip($0) }
                    .sorted { $0.gameTime < $1.gameTime }
                
                // Load recommended picks and results
                async let resultsTask = fetchGameResults(for: selectedDate)
                async let recommendedTask = loadRecommendedGames(from: betSlips)
                
                let (results, recommendedGames) = try await (resultsTask, recommendedTask)
                
                // Cache results
                gameResultsCache[cacheKey] = results
                
                self.allGames = allGames
                self.recommendedGames = recommendedGames
                self.gameResults = results
                self.lastLoadedDate = cacheKey
                
                applyFilters()
                isLoading = false
                
                print("✅ Loaded \(allGames.count) games, \(recommendedGames.count) recommended, \(results.count) results")
            } catch {
                self.errorMessage = "Failed to load predictions: \(error.localizedDescription)"
                self.isLoading = false
                print("❌ Error loading predictions: \(error)")
            }
        }
        
        // Clear cache when needed
        func clearCache() {
            betSlipsCache.removeAll()
            gameResultsCache.removeAll()
            print("🗑️ Cleared all caches")
        }
    
    // MARK: - Date Navigation
    func goToPreviousDay() async {
        selectedDate = Calendar.current.date(byAdding: .day, value: -1, to: selectedDate) ?? selectedDate
        await loadPredictions()
    }
    
    func goToNextDay() async {
        let tomorrow = Calendar.current.date(byAdding: .day, value: 1, to: Date()) ?? Date()
        if selectedDate < tomorrow {
            selectedDate = Calendar.current.date(byAdding: .day, value: 1, to: selectedDate) ?? selectedDate
            await loadPredictions()
        }
    }
    
    func goToToday() async {
        selectedDate = Date()
        await loadPredictions()
    }
    
    // MARK: - Load All Games
    private func loadAllGames() async throws -> [PredictionGame] {
        print("🔄 Loading all games for \(selectedDate)...")
        
        // Pass the selected date to fetchBetSlips
        let betSlips = try await firebaseService.fetchBetSlips(for: selectedDate)
        print("📊 Fetched \(betSlips.count) bet slips")
        
        await loadGameStatuses(for: betSlips.map { $0.gameID })
        
        let games = betSlips.compactMap { betSlip -> PredictionGame? in
            createPredictionGameFromBetSlip(betSlip)
        }
        
        return games.sorted { $0.gameTime < $1.gameTime }
    }
    
    // MARK: - Load Recommended Games from top_picks
    // MARK: - Load Recommended Games from top_picks
    // MARK: - Load Recommended Games from top_picks
    private func loadRecommendedGames(from betSlips: [BetSlip]) async throws -> [PredictionGame] {
        print("🔄 Loading recommended games from top_picks...")
        
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let dateStr = dateFormatter.string(from: selectedDate)
        
        do {
            let topPicksDoc = try await Firestore.firestore()
                .collection("games")
                .document(dateStr)
                .collection("picks_metadata")
                .document("top_picks")
                .getDocument()
            
            guard topPicksDoc.exists,
                  let data = topPicksDoc.data(),
                  let picksArray = data["picks"] as? [[String: Any]] else {
                print("⚠️ No top picks found for \(dateStr)")
                return []
            }
            
            print("✅ Found \(picksArray.count) top picks")
            
            // Create lookup from already-fetched bet slips
            var betSlipLookup: [String: BetSlip] = [:]
            for betSlip in betSlips {
                betSlipLookup[betSlip.gameID] = betSlip
            }
            
            var recommendedGames: [PredictionGame] = []
            
            for (index, pickData) in picksArray.enumerated() {
                guard let gameID = pickData["game_id"] as? String,
                      let betSlip = betSlipLookup[gameID] else {
                    continue
                }
                
                if let game = createPredictionGameFromTopPick(
                    betSlip: betSlip,
                    pickData: pickData,
                    ranking: index
                ) {
                    recommendedGames.append(game)
                }
            }
            
            return recommendedGames
        } catch {
            print("❌ Error loading top picks: \(error)")
            return []
        }
    }
    
    // MARK: - Create PredictionGame from BetSlip
    private func createPredictionGameFromBetSlip(_ betSlip: BetSlip) -> PredictionGame? {
        let spreadOdds = betSlip.bettingLines.spread["homeOdds"] ?? -110.0
        
        let bestBet = BestBet(
            type: .spread,
            selection: betSlip.homeTeam.name,
            odds: spreadOdds,
            sportsbook: betSlip.sportsbook
        )
        
        var keyFactors: [String] = []
        
        if let homeRank = betSlip.homeRanking {
            keyFactors.append("Home Rank: #\(homeRank)")
        }
        if let awayRank = betSlip.awayRanking {
            keyFactors.append("Away Rank: #\(awayRank)")
        }
        if let homeConf = betSlip.homeConference {
            keyFactors.append("Home: \(homeConf)")
        }
        if let awayConf = betSlip.awayConference {
            keyFactors.append("Away: \(awayConf)")
        }
        
        return PredictionGame(
            homeTeam: betSlip.homeTeam,
            awayTeam: betSlip.awayTeam,
            gameTime: betSlip.gameTime,
            bestBet: bestBet,
            confidence: 50.0,
            analysis: nil,
            keyFactors: keyFactors,
            betSlip: betSlip
        )
    }
    
    // MARK: - Create PredictionGame from Top Pick
    private func createPredictionGameFromTopPick(
        betSlip: BetSlip,
        pickData: [String: Any],
        ranking: Int
    ) -> PredictionGame? {
        guard
            let betType = pickData["bet_type"] as? String,
            let bookLine = pickData["book_line"] as? Double,
            let bookmaker = pickData["bookmaker"] as? String,
            let edgeStrength = pickData["edge_strength"] as? Double,
            let selection = pickData["selection"] as? String
        else {
            return nil
        }
        
        let modelProjection = pickData["model_projection"] as? Double
        let odds = pickData["odds"] as? Double ?? -110.0
        
        let oddsToProbDouble: Double
        if let probStr = pickData["odds_to_prob"] as? String {
            oddsToProbDouble = Double(probStr) ?? 0.0
        } else if let probDouble = pickData["odds_to_prob"] as? Double {
            oddsToProbDouble = probDouble
        } else {
            oddsToProbDouble = 0.0
        }
        
        let betTypeEnum: BetType
        if betType.lowercased() == "total" {
            betTypeEnum = .total
        } else if betType.lowercased() == "moneyline" {
            betTypeEnum = .moneyline
        } else {
            betTypeEnum = .spread
        }
        
        var sportsbookEnum: Sportsbook = .draftkings
        if let sbEnum = Sportsbook.allCases.first(where: { $0.rawValue.lowercased() == bookmaker.lowercased() }) {
            sportsbookEnum = sbEnum
        }
        
        let bestBet = BestBet(
            type: betTypeEnum,
            selection: selection,
            odds: odds,
            sportsbook: sportsbookEnum
        )
        
        var keyFactors: [String] = [
            "Ranking: \(ranking + 1)",
            "Book Line: \(bookLine)",
            "Edge Strength: \(String(format: "%.2f", edgeStrength))"
        ]
        
        if let modelProj = modelProjection {
            keyFactors.append("Model Projection: \(String(format: "%.2f", modelProj))")
        }
        
        if oddsToProbDouble > 0 {
            let percentage = oddsToProbDouble * 100
            keyFactors.append("Win Probability: \(String(format: "%.1f", percentage))%")
        }
        
        let confidence = min(max(50 + edgeStrength * 5, 50), 95)
        
        return PredictionGame(
            homeTeam: betSlip.homeTeam,
            awayTeam: betSlip.awayTeam,
            gameTime: betSlip.gameTime,
            bestBet: bestBet,
            confidence: confidence,
            analysis: "Edge strength: \(String(format: "%.1f", edgeStrength * 100))pts, Win probability: \(String(format: "%.1f", oddsToProbDouble * 100))%",
            keyFactors: keyFactors,
            betSlip: betSlip
        )
    }
    
    // MARK: - Helper Functions
    private func fetchGameData(gameID: String) async -> [String: Any]? {
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard gameIDComponents.count >= 2 else {
            return nil
        }
        
        let dateStr = gameIDComponents[0]
        
        do {
            let gameDoc = try await Firestore.firestore()
                .collection("games")
                .document(dateStr)
                .collection("games")
                .document(gameID)
                .getDocument()
            
            return gameDoc.data()
        } catch {
            print("❌ Error fetching game data: \(error)")
            return nil
        }
    }
    
    private func createBetSlipFromGameData(gameData: [String: Any]) async throws -> BetSlip? {
        // Placeholder - needs implementation
        return nil
    }
    
    private func loadGameStatuses(for gameIDs: [String]) async {
        for gameID in gameIDs {
            gameStatusCache[gameID] = GameStatus.notPlayed
        }
    }
    
    
        
    func applyFilters() {
        let sourceGames = viewMode == .allGames ? allGames : recommendedGames
        
        var filtered = sourceGames
        
        // Only apply filters in All Games mode
        if viewMode == .allGames {
            // Filter by conference
            if selectedConference != .all {
                filtered = filtered.filter { game in
                    let homeConf = game.betSlip.homeConference?.uppercased() ?? ""
                    let awayConf = game.betSlip.awayConference?.uppercased() ?? ""
                    let filterConf = selectedConference.rawValue.uppercased()
                    
                    // Match if either team is in the selected conference
                    return homeConf.contains(filterConf) || awayConf.contains(filterConf)
                }
            }
            
            // Filter by ranking
            switch selectedRanking {
            case .all:
                break
            case .top25:
                filtered = filtered.filter { game in
                    (game.betSlip.homeRanking ?? 999) <= 25 || (game.betSlip.awayRanking ?? 999) <= 25
                }
            case .top50:
                filtered = filtered.filter { game in
                    (game.betSlip.homeRanking ?? 999) <= 50 || (game.betSlip.awayRanking ?? 999) <= 50
                }
            }
        }
        
        self.filteredGames = filtered
    }
    
    func switchViewMode(to mode: PredictionsViewMode) {
        viewMode = mode
        
        // Reset filters when switching to Recommended
        if mode == .recommended {
            selectedConference = .all
            selectedRanking = .all
        }
        
        applyFilters()
    }
    
    func updateConferenceFilter(_ filter: ConferenceFilter) {
        selectedConference = filter
        applyFilters()
    }
    
    func updateRankingFilter(_ filter: RankingFilter) {
        selectedRanking = filter
        applyFilters()
    }
    
    // MARK: - Refresh
    func refreshPredictions() async {
        print("🔄 Force refreshing predictions...")
        lastLoadedDate = nil
        await loadPredictions()
    }
    
    // MARK: - Bet Tracking
    func trackSpecificBet(from prediction: PredictionGame, betType: BetType, selection: String, odds: Double, amount: Double) async {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to track bets"
            return
        }
        
        let bet = Bet(
            id: UUID().uuidString,
            userID: currentUser.uid,
            gameID: prediction.betSlip.gameID,
            type: betType,
            selection: selection,
            odds: odds,
            amount: amount,
            result: .pending,
            placedAt: Date()
        )
        
        do {
            try await firebaseService.addUserBet(bet)
            errorMessage = nil
        } catch {
            errorMessage = "Failed to track bet: \(error.localizedDescription)"
        }
    }
    
    func trackBet(from prediction: PredictionGame) async {
        await trackSpecificBet(
            from: prediction,
            betType: prediction.bestBet.type,
            selection: prediction.bestBet.selection,
            odds: prediction.bestBet.odds,
            amount: 0.0
        )
    }
}
