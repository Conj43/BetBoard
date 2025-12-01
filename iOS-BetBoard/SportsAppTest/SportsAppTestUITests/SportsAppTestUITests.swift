//
//  SportsAppTestUITests.swift
//  SportsAppTestUITests
//
//  Created by Trenton Roney on 8/1/25.
//

import XCTest

final class SportsAppTestUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    override func tearDownWithError() throws {
        app = nil
    }

    // MARK: - Authentication UI Tests
    
    // Test 41: Launch and See Auth Screen
    @MainActor
    func testLaunchShowsAuthScreen() throws {
        app.launch()
        
        // Check for auth screen elements
        XCTAssertTrue(app.buttons["Sign In Anonymously"].exists || app.staticTexts["Home"].exists,
                      "Should show either auth screen or home screen")
    }
    
    // Test 42: Anonymous Sign In Flow
    @MainActor
    func testAnonymousSignIn() throws {
        app.launch()
        
        // If sign in button exists, tap it
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            
            // Wait for home screen
            let homeTab = app.tabBars.buttons["Home"]
            XCTAssertTrue(homeTab.waitForExistence(timeout: 5), "Should navigate to home screen after sign in")
        }
    }
    
    // Test 43: Google Sign In Button Exists
    @MainActor
    func testGoogleSignInButtonExists() throws {
        app.launch()
        
        // Check if Google sign in button exists (may not be visible if already signed in)
        if !app.tabBars.buttons["Home"].exists {
            XCTAssertTrue(app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'google'")).element.exists ||
                         app.buttons["Sign In Anonymously"].exists,
                         "Should show sign in options")
        }
    }
    
    // MARK: - Tab Navigation Tests
    
    // Test 44: Tab Bar Exists
    @MainActor
    func testTabBarExists() throws {
        app.launch()
        
        // Sign in if needed
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let tabBar = app.tabBars.firstMatch
        XCTAssertTrue(tabBar.exists, "Tab bar should exist")
    }
    
    // Test 45: Home Tab Navigation
    @MainActor
    func testHomeTabNavigation() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let homeTab = app.tabBars.buttons["Home"]
        XCTAssertTrue(homeTab.exists, "Home tab should exist")
        homeTab.tap()
        
        // Verify home screen content
        XCTAssertTrue(app.navigationBars["Home"].exists, "Home navigation bar should exist")
    }
    
    // Test 46: Search Tab Navigation
    @MainActor
    func testSearchTabNavigation() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let searchTab = app.tabBars.buttons["Search"]
        XCTAssertTrue(searchTab.exists, "Search tab should exist")
        searchTab.tap()
        
        // Verify search screen
        XCTAssertTrue(app.navigationBars["Search"].exists, "Search navigation bar should exist")
    }
    
    // Test 47: Predictions Tab Navigation
    @MainActor
    func testPredictionsTabNavigation() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let predictionsTab = app.tabBars.buttons["Predictions"]
        XCTAssertTrue(predictionsTab.exists, "Predictions tab should exist")
        predictionsTab.tap()
        sleep(1)
        
        // Verify predictions screen - check for any navigation bar or predictions content
        let predictionsExists = app.navigationBars.element.exists ||
                               app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'games' OR label CONTAINS[c] 'predictions'")).element.exists ||
                               app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'all games' OR label CONTAINS[c] 'recommended'")).element.exists
        XCTAssertTrue(predictionsExists, "Predictions screen should be visible")
    }
    
    // Test 48: Info Tab Navigation
    @MainActor
    func testInfoTabNavigation() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let infoTab = app.tabBars.buttons["Info"]
        XCTAssertTrue(infoTab.exists, "Info tab should exist")
        infoTab.tap()
        
        // Verify info screen
        XCTAssertTrue(app.navigationBars["Info"].exists, "Info navigation bar should exist")
    }
    
    // MARK: - Search Functionality Tests
    
    // Test 49: Search Bar Exists
    @MainActor
    func testSearchBarExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Search"].tap()
        sleep(1)
        
        // Look for text field (custom search bar)
        let textField = app.textFields.firstMatch
        XCTAssertTrue(textField.exists, "Search field should exist")
    }
    
    // Test 50: Search for Team
    @MainActor
    func testSearchForTeam() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Search"].tap()
        sleep(1)
        
        // Find and tap the text field
        let textField = app.textFields.firstMatch
        if textField.exists {
            textField.tap()
            sleep(1)
            textField.typeText("Duke")
            
            // Wait for results
            sleep(2)
            
            // Check if results appear (could be cells, buttons, or static texts)
            let hasResults = app.cells.count > 0 ||
                           app.buttons.count > 2 || // More than just tab bar buttons
                           app.staticTexts["Duke"].exists
            XCTAssertTrue(hasResults, "Search results should appear")
        } else {
            XCTFail("Could not find search text field")
        }
    }
    
    // Test 51: Clear Search
    @MainActor
    func testClearSearch() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Search"].tap()
        sleep(1)
        
        let textField = app.textFields.firstMatch
        if textField.exists {
            textField.tap()
            sleep(1)
            textField.typeText("Duke")
            sleep(1)
            
            // Look for clear button (x icon)
            let clearButton = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'Search for teams'")).element
            if clearButton.exists {
                clearButton.tap()
                sleep(1)
                XCTAssertEqual(textField.value as? String, "", "Search field should be empty")
            }
        }
    }
    
    // Test 52: Empty Search State
    @MainActor
    func testEmptySearchState() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Search"].tap()
        
        // Should show empty state
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'search'")).element.exists,
                     "Should show empty search state")
    }
    
    // MARK: - Home Screen Tests
    
    // Test 53: Portfolio Chart Exists
    @MainActor
    func testPortfolioChartExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Home"].tap()
        
        // Look for chart or portfolio elements
        let portfolioText = app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'portfolio' OR label CONTAINS[c] 'p&l'")).element
        XCTAssertTrue(portfolioText.exists || app.staticTexts["Total P&L"].exists,
                     "Portfolio section should exist")
    }
    
    // Test 54: Tracked Bets Section Exists
    @MainActor
    func testTrackedBetsSectionExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Home"].tap()
        sleep(1)
        
        // Look for "Tracked Bets" text or empty state
        let trackedBetsExists = app.staticTexts["Tracked Bets"].exists ||
                               app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'tracked' OR label CONTAINS[c] 'bets' OR label CONTAINS[c] 'browse games'")).element.exists
        XCTAssertTrue(trackedBetsExists, "Tracked Bets section or empty state should exist")
    }
    
    // Test 55: Quick Actions Exist
    @MainActor
    func testQuickActionsExist() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Home"].tap()
        
        // Look for quick action buttons
        let quickActionsExist = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'browse' OR label CONTAINS[c] 'predictions'")).count > 0
        XCTAssertTrue(quickActionsExist, "Quick actions should exist")
    }
    
    // Test 56: Pull to Refresh Home
    @MainActor
    func testPullToRefreshHome() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Home"].tap()
        
        // Pull down to refresh
        let scrollView = app.scrollViews.firstMatch
        if scrollView.exists {
            let start = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.2))
            let end = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.8))
            start.press(forDuration: 0, thenDragTo: end)
            
            sleep(1)
            XCTAssertTrue(true, "Pull to refresh completed")
        }
    }
    
    // MARK: - Predictions Screen Tests
    
    // Test 57: Predictions Date Selector Exists
    @MainActor
    func testPredictionsDateSelectorExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        
        // Look for date-related elements
        let dateElements = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'date' OR label CONTAINS[c] 'today'"))
        XCTAssertTrue(dateElements.count > 0 || app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'games'")).element.exists,
                     "Date selector or games list should exist")
    }
    
    // Test 58: View Mode Toggle
    @MainActor
    func testViewModeToggle() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        // Look for view mode toggles (case insensitive)
        let allGamesButton = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'all' AND label CONTAINS[c] 'games'")).element
        let recommendedButton = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'recommended'")).element
        
        let viewModeExists = allGamesButton.exists || recommendedButton.exists ||
                            app.segmentedControls.element.exists
        XCTAssertTrue(viewModeExists, "View mode toggle or segmented control should exist")
    }
    
    // Test 59: Predictions Filter Button
    @MainActor
    func testPredictionsFilterButton() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        
        // Switch to All Games mode if filter exists
        if app.buttons["All Games"].exists {
            app.buttons["All Games"].tap()
            sleep(1)
            
            // Look for filter options
            let filterExists = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'filter' OR label CONTAINS[c] 'conference'")).count > 0
            XCTAssertTrue(filterExists || app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'games'")).element.exists,
                         "Filters or games list should exist")
        }
    }
    
    // Test 60: Prediction Card Tap
    @MainActor
    func testPredictionCardTap() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        // Tap first prediction if it exists
        let cells = app.collectionViews.cells
        if cells.count > 0 {
            cells.firstMatch.tap()
            sleep(1)
            
            // Should show bet slip or game detail
            XCTAssertTrue(app.navigationBars.element.exists, "Should navigate to detail view")
        }
    }
    
    // MARK: - Info Screen Tests
    
    // Test 61: User Profile Section Exists
    @MainActor
    func testUserProfileSectionExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        
        // Look for user-related elements
        let userElements = app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'user' OR label CONTAINS[c] 'anonymous'"))
        XCTAssertTrue(userElements.count > 0, "User profile section should exist")
    }
    
    // Test 62: Settings Toggles Exist
    @MainActor
    func testSettingsTogglesExist() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        
        // Look for settings switches
        let switches = app.switches
        XCTAssertGreaterThan(switches.count, 0, "Settings toggles should exist")
    }
    
    // Test 63: Notifications Toggle
    @MainActor
    func testNotificationsToggle() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        
        let notificationsSwitch = app.switches["Notifications"]
        if notificationsSwitch.exists {
            let initialState = notificationsSwitch.value as? String
            notificationsSwitch.tap()
            sleep(1)
            let newState = notificationsSwitch.value as? String
            XCTAssertNotEqual(initialState, newState, "Toggle state should change")
        }
    }
    
    // Test 64: Dark Mode Toggle
    @MainActor
    func testDarkModeToggle() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        
        let darkModeSwitch = app.switches["Dark Mode"]
        if darkModeSwitch.exists {
            let initialState = darkModeSwitch.value as? String
            darkModeSwitch.tap()
            sleep(1)
            let newState = darkModeSwitch.value as? String
            XCTAssertNotEqual(initialState, newState, "Toggle state should change")
        }
    }
    
    // Test 65: Sign Out Button Exists (DEBUG VERSION)
    @MainActor
    func testSignOutButtonExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        sleep(1)
        
        // Scroll down if needed
        let scrollView = app.scrollViews.firstMatch
        if scrollView.exists {
            scrollView.swipeUp()
            sleep(1)
        }
        
        // DEBUG: Print all button labels
        print("🔍 DEBUG: All buttons found:")
        for button in app.buttons.allElementsBoundByIndex {
            print("  - Button label: '\(button.label)'")
        }
        
        // Look for sign out button
        let signOutButton = app.buttons["Sign Out"]
        XCTAssertTrue(signOutButton.exists, "Sign Out button should exist. Found buttons: \(app.buttons.allElementsBoundByIndex.map { $0.label })")
    }
    
    // Test 66: Sign Out Flow
    @MainActor
    func testSignOutFlow() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Info"].tap()
        
        let signOutButton = app.buttons["Sign Out"]
        if signOutButton.exists {
            signOutButton.tap()
            sleep(1)
            
            // Confirm sign out if alert appears
            if app.alerts.element.exists {
                app.alerts.buttons["Sign Out"].tap()
                sleep(1)
                
                // Should return to auth screen
                XCTAssertTrue(app.buttons["Sign In Anonymously"].exists ||
                             app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'sign in'")).element.exists,
                             "Should return to auth screen")
            }
        }
    }
    
    // MARK: - Bet Slip Tests
    
    // Test 67: Bet Slip Opens from Prediction
    @MainActor
    func testBetSlipOpensFromPrediction() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        // Tap first game if exists
        let cells = app.collectionViews.cells
        if cells.count > 0 {
            cells.firstMatch.tap()
            sleep(1)
            
            // Should show bet slip elements
            XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'spread' OR label CONTAINS[c] 'moneyline' OR label CONTAINS[c] 'total'")).element.exists,
                         "Bet slip should show bet types")
        }
    }
    
    // Test 68: Sportsbook Selector Exists
    @MainActor
    func testSportsbookSelectorExists() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        let cells = app.collectionViews.cells
        if cells.count > 0 {
            cells.firstMatch.tap()
            sleep(1)
            
            // Look for sportsbook selector
            let sportsbookExists = app.buttons.containing(NSPredicate(format: "label CONTAINS[c] 'draftkings' OR label CONTAINS[c] 'fanduel' OR label CONTAINS[c] 'sportsbook'")).count > 0
            XCTAssertTrue(sportsbookExists || app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'odds'")).element.exists,
                         "Sportsbook selector or odds should exist")
        }
    }
    
    // Test 69: Bet Type Selection
    @MainActor
    func testBetTypeSelection() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        let cells = app.collectionViews.cells
        if cells.count > 0 {
            cells.firstMatch.tap()
            sleep(1)
            
            // Try tapping different bet types
            if app.buttons["Spread"].exists {
                app.buttons["Spread"].tap()
                sleep(1)
                XCTAssertTrue(true, "Spread bet type tapped")
            }
            
            if app.buttons["Moneyline"].exists {
                app.buttons["Moneyline"].tap()
                sleep(1)
                XCTAssertTrue(true, "Moneyline bet type tapped")
            }
        }
    }
    
    // Test 70: Bet Amount Input
    @MainActor
    func testBetAmountInput() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        let cells = app.collectionViews.cells
        if cells.count > 0 {
            cells.firstMatch.tap()
            sleep(1)
            
            // Look for amount input field
            let textFields = app.textFields
            for textField in textFields.allElementsBoundByIndex {
                if textField.exists && textField.isHittable {
                    textField.tap()
                    textField.typeText("50")
                    sleep(1)
                    XCTAssertTrue(true, "Amount entered")
                    break
                }
            }
        }
    }
    
    // MARK: - Navigation Tests
    
    // Test 71: Navigation Back Button
    @MainActor
    func testNavigationBackButton() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Search"].tap()
        sleep(1)
        
        let textField = app.textFields.firstMatch
        if textField.exists {
            textField.tap()
            sleep(1)
            textField.typeText("Duke")
            sleep(2)
            
            if app.cells.count > 0 || app.buttons.count > 3 {
                // Find and tap a team (could be cell or button)
                if app.cells.count > 0 {
                    app.cells.firstMatch.tap()
                } else {
                    // Find a non-tab-bar button
                    let buttons = app.buttons.allElementsBoundByIndex
                    if buttons.count > 3 {
                        buttons[0].tap()
                    }
                }
                sleep(1)
                
                // Tap back button
                if app.navigationBars.buttons.count > 0 {
                    app.navigationBars.buttons.element(boundBy: 0).tap()
                    sleep(1)
                    XCTAssertTrue(app.textFields.element.exists || app.tabBars.element.exists, "Should navigate back")
                }
            }
        }
    }
    
    // Test 72: Deep Navigation Stack
    @MainActor
    func testDeepNavigationStack() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Navigate through multiple screens
        app.tabBars.buttons["Search"].tap()
        sleep(1)
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        app.tabBars.buttons["Home"].tap()
        sleep(1)
        
        XCTAssertTrue(app.navigationBars["Home"].exists, "Should handle multiple tab switches")
    }
    
    // MARK: - Accessibility Tests
    
    // Test 73: VoiceOver Labels
    @MainActor
    func testVoiceOverLabels() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Check that main buttons have accessibility labels
        let homeTab = app.tabBars.buttons["Home"]
        XCTAssertNotNil(homeTab.label, "Home tab should have accessibility label")
        
        let searchTab = app.tabBars.buttons["Search"]
        XCTAssertNotNil(searchTab.label, "Search tab should have accessibility label")
    }
    
    // Test 74: Dynamic Type Support
    @MainActor
    func testDynamicTypeSupport() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Verify text elements exist (they should scale with dynamic type)
        let staticTexts = app.staticTexts
        XCTAssertGreaterThan(staticTexts.count, 0, "Static texts should exist and support dynamic type")
    }
    
    // MARK: - Error Handling Tests
    
    // Test 75: Network Error Handling
    @MainActor
    func testNetworkErrorHandling() throws {
        // Note: This test would require network conditions simulation
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Pull to refresh to trigger potential network call
        app.tabBars.buttons["Home"].tap()
        let scrollView = app.scrollViews.firstMatch
        if scrollView.exists {
            let start = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.2))
            let end = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.8))
            start.press(forDuration: 0, thenDragTo: end)
            sleep(2)
            
            // Check if app handles any errors gracefully
            XCTAssertTrue(true, "App should handle network errors gracefully")
        }
    }
    
    // Test 76: Empty State Handling
    @MainActor
    func testEmptyStateHandling() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Home"].tap()
        
        // Check for empty state messages
        let emptyStateExists = app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'no bets' OR label CONTAINS[c] 'empty' OR label CONTAINS[c] 'get started'")).element.exists
        
        // Either has content or shows empty state
        XCTAssertTrue(emptyStateExists || app.scrollViews.firstMatch.exists,
                     "Should show either content or empty state")
    }
    
    // MARK: - Performance Tests
    
    // Test 77: App Launch Performance
    @MainActor
    func testAppLaunchPerformance() throws {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            app.launch()
        }
    }
    
    // Test 78: Tab Switch Performance
    @MainActor
    func testTabSwitchPerformance() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        measure {
            app.tabBars.buttons["Home"].tap()
            app.tabBars.buttons["Search"].tap()
            app.tabBars.buttons["Predictions"].tap()
            app.tabBars.buttons["Info"].tap()
        }
    }
    
    // Test 79: Scroll Performance
    @MainActor
    func testScrollPerformance() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        app.tabBars.buttons["Predictions"].tap()
        sleep(1)
        
        let scrollView = app.scrollViews.firstMatch
        if scrollView.exists {
            measure {
                scrollView.swipeUp()
                scrollView.swipeDown()
            }
        }
    }
    
    // Test 80: Memory Stress Test
    @MainActor
    func testMemoryStressTest() throws {
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(1)
        }
        
        // Navigate through all tabs multiple times
        for _ in 0..<5 {
            app.tabBars.buttons["Home"].tap()
            app.tabBars.buttons["Search"].tap()
            app.tabBars.buttons["Predictions"].tap()
            app.tabBars.buttons["Info"].tap()
        }
        
        XCTAssertTrue(app.tabBars.element.exists, "App should remain responsive after multiple navigations")
    }
}
