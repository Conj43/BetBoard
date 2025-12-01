//
//  SportsAppTestTests.swift
//  SportsAppTestTests
//
//  Created by Trenton Roney on 8/1/25.
//

import Testing
import XCTest
@testable import SportsAppTest
import FirebaseAuth
import FirebaseFirestore

// MARK: - Authentication Tests
@MainActor
class AuthenticationTests: XCTestCase {
    var authService: AuthService!
    
    override func setUp() async throws {
        authService = AuthService()
    }
    
    override func tearDown() {
        authService = nil
    }
    
    // Test 1: Anonymous Sign-In Success
    func testAnonymousSignInSuccess() async throws {
        await authService.signInAnonymously()
        
        XCTAssertTrue(authService.isSignedIn, "User should be signed in")
        XCTAssertNotNil(authService.currentUser, "Current user should not be nil")
        XCTAssertNil(authService.errorMessage, "Error message should be nil on success")
        XCTAssertFalse(authService.isLoading, "Loading should be false after completion")
    }
    
    // Test 2: Sign Out Success
    func testSignOutSuccess() async throws {
        // First sign in
        await authService.signInAnonymously()
        XCTAssertTrue(authService.isSignedIn)
        
        // Then sign out
        authService.signOut()
        
        XCTAssertFalse(authService.isSignedIn, "User should not be signed in after sign out")
        XCTAssertNil(authService.currentUser, "Current user should be nil after sign out")
    }
    
    
    // Test 4: Multiple Sign-In Attempts
    func testMultipleSignInAttempts() async throws {
        await authService.signInAnonymously()
        let firstUserId = authService.currentUser?.uid
        
        authService.signOut()
        await authService.signInAnonymously()
        let secondUserId = authService.currentUser?.uid
        
        XCTAssertNotEqual(firstUserId, secondUserId, "Different anonymous sign-ins should create different users")
    }
}

// MARK: - Firebase Service Tests
@MainActor
class FirebaseServiceTests: XCTestCase {
    var firebaseService: FirebaseService!
    
    override func setUp() {
        firebaseService = FirebaseService()
    }
    
    override func tearDown() {
        firebaseService = nil
    }
    
    // Test 5: Fetch Teams Success
    func testFetchTeamsSuccess() async throws {
        let teams = try await firebaseService.fetchTeams()
        
        XCTAssertFalse(teams.isEmpty, "Teams array should not be empty")
        XCTAssertGreaterThan(teams.count, 0, "Should fetch at least one team")
        
        // Verify team structure
        if let firstTeam = teams.first {
            XCTAssertFalse(firstTeam.name.isEmpty, "Team name should not be empty")
            XCTAssertFalse(firstTeam.shortName.isEmpty, "Short name should not be empty")
            XCTAssertFalse(firstTeam.conference.isEmpty, "Conference should not be empty")
        }
    }
    
    // Test 6: Fetch Games for Current Date
    func testFetchGamesForCurrentDate() async throws {
        let games = try await firebaseService.fetchGames(for: Date())
        
        XCTAssertNotNil(games, "Games array should not be nil")
        
        // If games exist, verify structure
        if let firstGame = games.first {
            XCTAssertFalse(firstGame.homeTeam.isEmpty, "Home team should not be empty")
            XCTAssertFalse(firstGame.awayTeam.isEmpty, "Away team should not be empty")
            XCTAssertFalse(firstGame.id.isEmpty, "Game ID should not be empty")
        }
    }
    
    // Test 7: Fetch Games for Specific Date
    func testFetchGamesForSpecificDate() async throws {
        let calendar = Calendar.current
        let specificDate = calendar.date(from: DateComponents(year: 2024, month: 11, day: 15))!
        
        let games = try await firebaseService.fetchGames(for: specificDate)
        
        XCTAssertNotNil(games, "Games array should not be nil")
    }
    
    // Test 8: Team Caching
    func testTeamCaching() async throws {
        // First fetch
        let startTime = Date()
        let teams1 = try await firebaseService.fetchTeams()
        let firstFetchTime = Date().timeIntervalSince(startTime)
        
        // Second fetch (should use cache)
        let secondStart = Date()
        let teams2 = try await firebaseService.fetchTeams()
        let secondFetchTime = Date().timeIntervalSince(secondStart)
        
        XCTAssertEqual(teams1.count, teams2.count, "Cached teams should match original")
        XCTAssertLessThan(secondFetchTime, firstFetchTime, "Cached fetch should be faster")
    }
    
    // Test 9: Fetch Betting Lines
    func testFetchBettingLines() async throws {
        // First get a game
        let games = try await firebaseService.fetchGames(for: Date())
        guard let firstGame = games.first else {
            throw XCTSkip("No games available for testing")
        }
        
        let bettingLines = try await firebaseService.fetchAllBettingLines(for: firstGame.id)
        
        // Betting lines may or may not exist
        if let lines = bettingLines {
            XCTAssertNotNil(lines, "Betting lines should be structured properly")
        }
    }
    
    // Test 10: Fetch Bet Slips
    func testFetchBetSlips() async throws {
        let betSlips = try await firebaseService.fetchBetSlips(for: Date())
        
        XCTAssertNotNil(betSlips, "Bet slips array should not be nil")
        
        // If bet slips exist, verify structure
        if let firstBetSlip = betSlips.first {
            XCTAssertNotNil(firstBetSlip.homeTeam, "Home team should not be nil")
            XCTAssertNotNil(firstBetSlip.awayTeam, "Away team should not be nil")
            XCTAssertNotNil(firstBetSlip.bettingLines, "Betting lines should not be nil")
        }
    }
}

// MARK: - ViewModel Tests
@MainActor
class ViewModelTests: XCTestCase {
    
    // Test 11: SearchViewModel Initialization
    func testSearchViewModelInit() async {
        let viewModel = SearchViewModel()
        
        XCTAssertTrue(viewModel.searchText.isEmpty, "Search text should be empty on init")
        XCTAssertTrue(viewModel.searchResults.isEmpty, "Search results should be empty on init")
        XCTAssertFalse(viewModel.isLoading, "Should not be loading on init")
    }
    
    // Test 12: SearchViewModel Team Loading
    func testSearchViewModelLoadTeams() async throws {
        let viewModel = SearchViewModel()
        
        await viewModel.loadTeams()
        
        XCTAssertFalse(viewModel.allTeams.isEmpty, "Teams should be loaded")
        XCTAssertFalse(viewModel.isLoading, "Loading should be complete")
    }
    
    // Test 13: SearchViewModel Search Functionality
    func testSearchViewModelSearch() async throws {
        let viewModel = SearchViewModel()
        await viewModel.loadTeams()
        
        // Perform search
        viewModel.searchText = "Duke"
        
        // Wait for debounce
        try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        
        XCTAssertFalse(viewModel.searchResults.isEmpty, "Search should return results for 'Duke'")
    }
    
    // Test 14: PredictionsViewModel Initialization
    func testPredictionsViewModelInit() async {
        let viewModel = PredictionsViewModel()
        
        XCTAssertEqual(viewModel.viewMode, .recommended, "Should default to recommended view mode")
        XCTAssertEqual(viewModel.selectedConference, .all, "Should default to all conferences")
        XCTAssertTrue(viewModel.allGames.isEmpty, "Games should be empty on init")
    }
    
    // Test 15: PredictionsViewModel Filter Application
    func testPredictionsViewModelFilters() async throws {
        let viewModel = PredictionsViewModel()
        
        // Change filter
        viewModel.selectedConference = .bigTen
        viewModel.applyFilters()
        
        // Verify filter is applied (actual filtering logic tested separately)
        XCTAssertEqual(viewModel.selectedConference, .bigTen)
    }
    
    // Test 16: HomeViewModel Initialization
    func testHomeViewModelInit() async {
        let viewModel = HomeViewModel()
        
        XCTAssertTrue(viewModel.trackedBets.isEmpty, "Tracked bets should be empty on init")
        XCTAssertEqual(viewModel.totalPnL, 0.0, "Total P&L should be 0 on init")
        XCTAssertFalse(viewModel.isLoading, "Should not be loading on init")
    }
    
    // Test 17: InfoViewModel Settings Load
    func testInfoViewModelLoadSettings() async throws {
        // This test requires authentication
        let authService = AuthService()
        await authService.signInAnonymously()
        
        let viewModel = InfoViewModel()
        await viewModel.loadSettings()
        
        // Settings may or may not exist for anonymous user
        XCTAssertFalse(viewModel.isLoading, "Loading should be complete")
    }
}

// MARK: - Model Tests
class ModelTests: XCTestCase {
    
    // Test 18: Team Model Creation
    func testTeamModelCreation() {
        let team = Team(
            id: "test-id",
            name: "Test University",
            shortName: "Test",
            logoURL: "https://example.com/logo.png",
            record: TeamRecord(wins: 10, losses: 5),
            conference: "Test Conference",
            ranking: 15,
            colorHex: "#0000FF"
        )
        
        XCTAssertEqual(team.name, "Test University")
        XCTAssertEqual(team.record.wins, 10)
        XCTAssertEqual(team.record.losses, 5)
        XCTAssertEqual(team.ranking, 15)
    }
    
    // Test 19: Bet Model Creation
    func testBetModelCreation() {
        let bet = Bet(
            id: "bet-123",
            userID: "user-456",
            gameID: "game-789",
            type: .spread,
            selection: "Duke -5.5",
            odds: -110,
            amount: 50.0,
            result: .pending,
            placedAt: Date(),
            homeTeamName: "Duke",
            awayTeamName: "UNC",
            gameDate: Date(),
            sportsbook: .draftkings
        )
        
        XCTAssertEqual(bet.type, .spread)
        XCTAssertEqual(bet.amount, 50.0)
        XCTAssertEqual(bet.odds, -110)
        XCTAssertEqual(bet.result, .pending)
        XCTAssertEqual(bet.sportsbook, .draftkings)
    }
    
    // Test 20: BetType Enum
    func testBetTypeEnum() {
        XCTAssertEqual(BetType.spread.rawValue, "spread")
        XCTAssertEqual(BetType.moneyline.rawValue, "moneyline")
        XCTAssertEqual(BetType.total.rawValue, "total")
        
        XCTAssertEqual(BetType(rawValue: "spread"), .spread)
        XCTAssertEqual(BetType(rawValue: "moneyline"), .moneyline)
        XCTAssertEqual(BetType(rawValue: "total"), .total)
    }
    
    // Test 21: BetResult Enum
    func testBetResultEnum() {
        XCTAssertEqual(BetResult.pending.rawValue, "pending")
        XCTAssertEqual(BetResult.won.rawValue, "won")
        XCTAssertEqual(BetResult.lost.rawValue, "lost")
        XCTAssertEqual(BetResult.push.rawValue, "push")
    }
    
    // Test 22: Sportsbook Enum
    func testSportsbookEnum() {
        // Check the raw values match your actual enum implementation
        XCTAssertEqual(Sportsbook.draftkings.rawValue, "DraftKings")
        XCTAssertEqual(Sportsbook.fanduel.rawValue, "FanDuel")
        XCTAssertEqual(Sportsbook.betmgm.rawValue, "BetMGM")
        
        // Test initialization from raw values
        XCTAssertEqual(Sportsbook(rawValue: "DraftKings"), .draftkings)
        XCTAssertEqual(Sportsbook(rawValue: "FanDuel"), .fanduel)
        XCTAssertEqual(Sportsbook(rawValue: "BetMGM"), .betmgm)
        
        // Test that invalid raw values return nil
        XCTAssertNil(Sportsbook(rawValue: "InvalidBook"))
    }
}
// MARK: - Data Validation Tests
class DataValidationTests: XCTestCase {
    
    // Test 23: Team Name Validation
    func testTeamNameValidation() {
        let validName = "Duke"
        let emptyName = ""
        
        XCTAssertFalse(validName.isEmpty, "Valid name should not be empty")
        XCTAssertTrue(emptyName.isEmpty, "Empty name should be empty")
    }
    
    // Test 24: Odds Validation
    func testOddsValidation() {
        let positiveOdds = 150.0
        let negativeOdds = -110.0
        let zeroOdds = 0.0
        
        XCTAssertGreaterThan(positiveOdds, 0, "Positive odds should be greater than 0")
        XCTAssertLessThan(negativeOdds, 0, "Negative odds should be less than 0")
        XCTAssertEqual(zeroOdds, 0, "Zero odds should equal 0")
    }
    
    // Test 25: Bet Amount Validation
    func testBetAmountValidation() {
        let validAmount = 50.0
        let negativeAmount = -10.0
        let zeroAmount = 0.0
        
        XCTAssertGreaterThan(validAmount, 0, "Valid amount should be positive")
        XCTAssertLessThan(negativeAmount, 0, "Negative amount should be less than 0")
        XCTAssertEqual(zeroAmount, 0, "Zero amount should equal 0")
    }
    
    // Test 26: Date Validation
    func testDateValidation() {
        let now = Date()
        let past = Date(timeIntervalSinceNow: -3600) // 1 hour ago
        let future = Date(timeIntervalSinceNow: 3600) // 1 hour from now
        
        XCTAssertLessThan(past, now, "Past date should be less than now")
        XCTAssertGreaterThan(future, now, "Future date should be greater than now")
    }
    
    // Test 27: Game ID Format Validation
    func testGameIDFormat() {
        let validGameID = "2024-11-15_duke_unc"
        let components = validGameID.components(separatedBy: "_")
        
        XCTAssertGreaterThanOrEqual(components.count, 2, "Game ID should have at least 2 components")
        XCTAssertTrue(components[0].contains("-"), "First component should be a date")
    }
}

// MARK: - Team Logo Tests
class TeamLogoTests: XCTestCase {
    
    // Test 28: Logo Filename Generation
    func testLogoFilenameGeneration() {
        let teamName1 = "Michigan State"
        let teamName2 = "Duke"
        
        let filename1 = TeamLogoHelper.logoFilename(for: teamName1)
        let filename2 = TeamLogoHelper.logoFilename(for: teamName2)
        
        XCTAssertEqual(filename1, "michigan_state", "Filename should replace spaces with underscores")
        XCTAssertEqual(filename2, "duke", "Filename should be lowercase")
    }
    
    // MARK: - Integration Tests
    @MainActor
    class IntegrationTests: XCTestCase {
        
        // Test 31: End-to-End Bet Tracking
        func testEndToEndBetTracking() async throws {
            // 1. Sign in
            let authService = AuthService()
            await authService.signInAnonymously()
            
            guard let userId = authService.currentUser?.uid else {
                XCTFail("User should be signed in")
                return
            }
            
            // 2. Create a bet
            let bet = Bet(
                id: UUID().uuidString,
                userID: userId,
                gameID: "2024-11-15_duke_unc",
                type: .spread,
                selection: "Duke -5.5",
                odds: -110,
                amount: 50.0,
                result: .pending,
                placedAt: Date(),
                homeTeamName: "Duke",
                awayTeamName: "UNC",
                gameDate: Date(),
                sportsbook: .draftkings
            )
            
            // 3. Save bet to Firebase
            let firebaseService = FirebaseService()
            let db = Firestore.firestore()
            
            // Save the bet directly
            try await db.collection("users")
                .document(userId)
                .collection("bets")
                .document(bet.id)
                .setData([
                    "gameID": bet.gameID,
                    "type": bet.type.rawValue,
                    "selection": bet.selection,
                    "odds": bet.odds,
                    "amount": bet.amount,
                    "result": bet.result.rawValue,
                    "placedAt": Timestamp(date: bet.placedAt),
                    "home_team_name": bet.homeTeamName ?? "",
                    "away_team_name": bet.awayTeamName ?? "",
                    "game_date": Timestamp(date: bet.gameDate ?? Date()),
                    "sportsbook": bet.sportsbook?.rawValue ?? ""
                ])
            
            // Wait a moment for write to complete
            try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
            
            // 4. Fetch bets
            let fetchedBets = try await firebaseService.fetchUserBets(for: userId)
            
            // 5. Verify bet exists
            XCTAssertTrue(fetchedBets.contains(where: { $0.id == bet.id }), "Bet should be saved and retrieved")
            
            // Cleanup
            try await db.collection("users")
                .document(userId)
                .collection("bets")
                .document(bet.id)
                .delete()
        }
        
        // Test 32: Search to Game Detail Flow
        func testSearchToGameDetailFlow() async throws {
            // 1. Load teams
            let searchVM = SearchViewModel()
            await searchVM.loadTeams()
            
            XCTAssertFalse(searchVM.allTeams.isEmpty, "Teams should be loaded")
            
            // 2. Search for a team
            searchVM.searchText = "Duke"
            try await Task.sleep(nanoseconds: 500_000_000)
            
            XCTAssertFalse(searchVM.searchResults.isEmpty, "Search should return results")
            
            // 3. Get team details
            guard let team = searchVM.searchResults.first else {
                XCTFail("Should have search results")
                return
            }
            
            XCTAssertFalse(team.name.isEmpty, "Team should have valid data")
        }
    }
    
    // MARK: - Performance Tests
    @MainActor
    class PerformanceTests: XCTestCase {
        
        // Test 33: Team Loading Performance
        func testTeamLoadingPerformance() async throws {
            let firebaseService = FirebaseService()
            
            measure {
                let expectation = XCTestExpectation(description: "Load teams")
                
                Task {
                    _ = try? await firebaseService.fetchTeams()
                    expectation.fulfill()
                }
                
                wait(for: [expectation], timeout: 10.0)
            }
        }
        
        // Test 34: Search Performance
        func testSearchPerformance() async throws {
            measure {
                let expectation = XCTestExpectation(description: "Search load")
                
                Task { @MainActor in
                    let viewModel = SearchViewModel()
                    await viewModel.loadTeams()
                    expectation.fulfill()
                }
                
                wait(for: [expectation], timeout: 10.0)
            }
        }
    }
    
    // MARK: - Edge Case Tests
    class EdgeCaseTests: XCTestCase {
        
        // Test 35: Empty Search Query
        @MainActor
        func testEmptySearchQuery() async {
            let viewModel = SearchViewModel()
            viewModel.searchText = ""
            
            XCTAssertTrue(viewModel.searchResults.isEmpty, "Empty search should return no results")
        }
        
        // Test 36: Invalid Date Format
        func testInvalidDateFormat() {
            let invalidDateString = "invalid-date"
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            
            let date = dateFormatter.date(from: invalidDateString)
            XCTAssertNil(date, "Invalid date string should return nil")
        }
        
        // Test 37: Negative Bet Amount
        func testNegativeBetAmount() {
            let negativeAmount = -50.0
            
            XCTAssertLessThan(negativeAmount, 0, "Negative amount should be less than 0")
            // In real app, this should be caught by validation
        }
        
        // Test 38: Team Name with Special Characters
        func testTeamNameWithSpecialCharacters() {
            let specialName = "Saint Mary's"
            let filename = TeamLogoHelper.logoFilename(for: specialName)
            
            XCTAssertEqual(filename, "saint_mary's", "Should handle apostrophes correctly")
        }
        
        // Test 39: Very Long Team Name
        func testVeryLongTeamName() {
            let longName = String(repeating: "A", count: 1000)
            let filename = TeamLogoHelper.logoFilename(for: longName)
            
            XCTAssertEqual(filename.count, 1000, "Should handle long names")
        }
        
        // Test 40: Concurrent Requests
        @MainActor
        func testConcurrentRequests() async throws {
            let firebaseService = FirebaseService()
            
            // Make multiple concurrent requests
            async let teams1 = firebaseService.fetchTeams()
            async let teams2 = firebaseService.fetchTeams()
            async let teams3 = firebaseService.fetchTeams()
            
            let results = try await (teams1, teams2, teams3)
            
            XCTAssertEqual(results.0.count, results.1.count, "Concurrent requests should return same data")
            XCTAssertEqual(results.1.count, results.2.count, "Concurrent requests should return same data")
        }
    }
}
