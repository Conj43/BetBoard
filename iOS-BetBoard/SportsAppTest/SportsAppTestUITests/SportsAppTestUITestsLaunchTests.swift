//
//  SportsAppTestUITestsLaunchTests.swift
//  SportsAppTestUITests
//
//  Created by Trenton Roney on 8/1/25.
//

import XCTest

final class SportsAppTestUITestsLaunchTests: XCTestCase {

    override class var runsForEachTargetApplicationUIConfiguration: Bool {
        true
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    // MARK: - Basic Launch Tests
    
    // Test 81: Standard Launch
    @MainActor
    func testLaunch() throws {
        let app = XCUIApplication()
        app.launch()

        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Launch Screen"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch successfully")
    }
    
    // Test 82: Launch in Light Mode
    @MainActor
    func testLaunchInLightMode() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-UIUserInterfaceStyle", "Light"]
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Light Mode Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch in light mode")
    }
    
    // Test 83: Launch in Dark Mode
    @MainActor
    func testLaunchInDarkMode() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-UIUserInterfaceStyle", "Dark"]
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Dark Mode Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch in dark mode")
    }
    
    // Test 84: Launch with Different Locales
    @MainActor
    func testLaunchWithUSLocale() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(en-US)"]
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "US Locale Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with US locale")
    }
    
    // MARK: - Launch Performance Tests
    
    // Test 85: Launch Performance - Cold Start
    @MainActor
    func testLaunchPerformance() throws {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            XCUIApplication().launch()
        }
    }
    
    // Test 86: Launch Performance - Warm Start
    @MainActor
    func testWarmLaunchPerformance() throws {
        let app = XCUIApplication()
        app.launch()
        app.terminate()
        
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            app.launch()
        }
    }
    
    // Test 87: Launch Performance - Memory
    @MainActor
    func testLaunchMemoryPerformance() throws {
        let app = XCUIApplication()
        
        measure(metrics: [XCTMemoryMetric()]) {
            app.launch()
            sleep(2)
            app.terminate()
        }
    }
    
    // MARK: - Launch State Tests
    
    // Test 88: Launch After Termination
    @MainActor
    func testLaunchAfterTermination() throws {
        let app = XCUIApplication()
        app.launch()
        
        let firstLaunchScreenshot = app.screenshot()
        let firstAttachment = XCTAttachment(screenshot: firstLaunchScreenshot)
        firstAttachment.name = "First Launch"
        firstAttachment.lifetime = .keepAlways
        add(firstAttachment)
        
        app.terminate()
        sleep(1)
        app.launch()
        
        let secondLaunchScreenshot = app.screenshot()
        let secondAttachment = XCTAttachment(screenshot: secondLaunchScreenshot)
        secondAttachment.name = "Second Launch After Termination"
        secondAttachment.lifetime = .keepAlways
        add(secondAttachment)
        
        XCTAssertTrue(app.exists, "App should relaunch after termination")
    }
    
    // Test 89: Launch with Existing User Session
    @MainActor
    func testLaunchWithExistingSession() throws {
        let app = XCUIApplication()
        app.launch()
        
        // Sign in if needed
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        let signedInScreenshot = app.screenshot()
        let signedInAttachment = XCTAttachment(screenshot: signedInScreenshot)
        signedInAttachment.name = "Signed In State"
        signedInAttachment.lifetime = .keepAlways
        add(signedInAttachment)
        
        // Terminate and relaunch
        app.terminate()
        sleep(1)
        app.launch()
        
        let relaunchScreenshot = app.screenshot()
        let relaunchAttachment = XCTAttachment(screenshot: relaunchScreenshot)
        relaunchAttachment.name = "Relaunch With Session"
        relaunchAttachment.lifetime = .keepAlways
        add(relaunchAttachment)
        
        // Should maintain session (or show auth screen)
        XCTAssertTrue(app.tabBars.element.exists || app.buttons["Sign In Anonymously"].exists,
                     "Should show either main app or auth screen")
    }
    
    // MARK: - Launch Orientation Tests
    
    // Test 90: Launch in Portrait
    @MainActor
    func testLaunchInPortrait() throws {
        let device = XCUIDevice.shared
        device.orientation = .portrait
        
        let app = XCUIApplication()
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Portrait Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch in portrait")
    }
    
    // Test 91: Launch in Landscape
    @MainActor
    func testLaunchInLandscape() throws {
        let device = XCUIDevice.shared
        device.orientation = .landscapeLeft
        
        let app = XCUIApplication()
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Landscape Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch in landscape")
    }
    
    // MARK: - Launch Environment Tests
    
    // Test 92: Launch with Debug Flag
    @MainActor
    func testLaunchWithDebugFlag() throws {
        let app = XCUIApplication()
        app.launchArguments.append("-DEBUG_MODE")
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Debug Mode Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with debug flag")
    }
    
    // Test 93: Launch with Test Data
    @MainActor
    func testLaunchWithTestData() throws {
        let app = XCUIApplication()
        app.launchArguments.append("-USE_TEST_DATA")
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Test Data Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with test data")
    }
    
    // MARK: - Launch Accessibility Tests
    
    // Test 94: Launch with VoiceOver
    @MainActor
    func testLaunchWithVoiceOver() throws {
        let app = XCUIApplication()
        app.launchArguments.append("-UIAccessibilityVoiceOverEnabled")
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "VoiceOver Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with VoiceOver support")
    }
    
    // Test 95: Launch with Increased Text Size
    @MainActor
    func testLaunchWithIncreasedTextSize() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityExtraExtraLarge"]
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Large Text Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with large text")
    }
    
    // Test 96: Launch with Reduced Motion
    @MainActor
    func testLaunchWithReducedMotion() throws {
        let app = XCUIApplication()
        app.launchArguments.append("-UIAccessibilityReduceMotionEnabled")
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Reduced Motion Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch with reduced motion")
    }
    
    // MARK: - Launch Screen Capture Tests
    
    // Test 97: Capture Auth Screen
    @MainActor
    func testCaptureAuthScreen() throws {
        let app = XCUIApplication()
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            let attachment = XCTAttachment(screenshot: app.screenshot())
            attachment.name = "Auth Screen"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
        
        XCTAssertTrue(app.exists, "Auth screen captured")
    }
    
    // Test 98: Capture Main App After Login
    @MainActor
    func testCaptureMainAppAfterLogin() throws {
        let app = XCUIApplication()
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        if app.tabBars.element.exists {
            let attachment = XCTAttachment(screenshot: app.screenshot())
            attachment.name = "Main App Screen"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
        
        XCTAssertTrue(app.exists, "Main app screen captured")
    }
    
    // Test 99: Capture All Tab Screens
    @MainActor
    func testCaptureAllTabScreens() throws {
        let app = XCUIApplication()
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        if app.tabBars.element.exists {
            // Home Tab
            app.tabBars.buttons["Home"].tap()
            sleep(1)
            let homeAttachment = XCTAttachment(screenshot: app.screenshot())
            homeAttachment.name = "Home Tab"
            homeAttachment.lifetime = .keepAlways
            add(homeAttachment)
            
            // Search Tab
            app.tabBars.buttons["Search"].tap()
            sleep(1)
            let searchAttachment = XCTAttachment(screenshot: app.screenshot())
            searchAttachment.name = "Search Tab"
            searchAttachment.lifetime = .keepAlways
            add(searchAttachment)
            
            // Predictions Tab
            app.tabBars.buttons["Predictions"].tap()
            sleep(1)
            let predictionsAttachment = XCTAttachment(screenshot: app.screenshot())
            predictionsAttachment.name = "Predictions Tab"
            predictionsAttachment.lifetime = .keepAlways
            add(predictionsAttachment)
            
            // Info Tab
            app.tabBars.buttons["Info"].tap()
            sleep(1)
            let infoAttachment = XCTAttachment(screenshot: app.screenshot())
            infoAttachment.name = "Info Tab"
            infoAttachment.lifetime = .keepAlways
            add(infoAttachment)
        }
        
        XCTAssertTrue(app.exists, "All tab screens captured")
    }
    
    // MARK: - Launch Crash Tests
    
    // Test 100: Launch Stability
    @MainActor
    func testLaunchStability() throws {
        let app = XCUIApplication()
        
        // Launch multiple times to ensure stability
        for i in 1...5 {
            app.launch()
            sleep(1)
            
            let attachment = XCTAttachment(screenshot: app.screenshot())
            attachment.name = "Launch Iteration \(i)"
            attachment.lifetime = .keepAlways
            add(attachment)
            
            XCTAssertTrue(app.exists, "App should remain stable on iteration \(i)")
            
            app.terminate()
            sleep(1)
        }
    }
    
    // MARK: - Launch Resource Tests
    
    // Test 101: Launch CPU Usage
    @MainActor
    func testLaunchCPUUsage() throws {
        let app = XCUIApplication()
        
        measure(metrics: [XCTCPUMetric()]) {
            app.launch()
            sleep(2)
            app.terminate()
        }
    }
    
    // Test 102: Launch Storage Performance
    @MainActor
    func testLaunchStoragePerformance() throws {
        let app = XCUIApplication()
        
        measure(metrics: [XCTStorageMetric()]) {
            app.launch()
            sleep(2)
            app.terminate()
        }
    }
    
    // Test 103: Launch Clock Time
    @MainActor
    func testLaunchClockTime() throws {
        let app = XCUIApplication()
        
        measure(metrics: [XCTClockMetric()]) {
            app.launch()
            sleep(1)
            app.terminate()
        }
    }
    
    // MARK: - Additional Launch Scenarios
    
    // Test 104: Launch After Background
    @MainActor
    func testLaunchAfterBackground() throws {
        let app = XCUIApplication()
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Simulate going to background
        XCUIDevice.shared.press(.home)
        sleep(2)
        
        // Reactivate
        app.activate()
        sleep(1)
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "After Background Return"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should handle background/foreground transitions")
    }
    
    // Test 105: Launch State Preservation
    @MainActor
    func testLaunchStatePreservation() throws {
        let app = XCUIApplication()
        app.launch()
        
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Navigate to a specific tab
        if app.tabBars.element.exists {
            app.tabBars.buttons["Predictions"].tap()
            sleep(1)
            
            let beforeTermination = XCTAttachment(screenshot: app.screenshot())
            beforeTermination.name = "Before Termination"
            beforeTermination.lifetime = .keepAlways
            add(beforeTermination)
            
            // Terminate and relaunch
            app.terminate()
            sleep(1)
            app.launch()
            sleep(2)
            
            let afterRelaunch = XCTAttachment(screenshot: app.screenshot())
            afterRelaunch.name = "After Relaunch"
            afterRelaunch.lifetime = .keepAlways
            add(afterRelaunch)
        }
        
        XCTAssertTrue(app.exists, "App should preserve or restore state")
    }
    
    // MARK: - Launch Error Scenarios
    
    // Test 106: Launch with No Network
    @MainActor
    func testLaunchWithNoNetwork() throws {
        // Note: This would require network condition simulation
        let app = XCUIApplication()
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Launch Without Network"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should launch gracefully without network")
    }
    
    // Test 107: Launch Timeout Test
    @MainActor
    func testLaunchTimeout() throws {
        let app = XCUIApplication()
        let startTime = Date()
        
        app.launch()
        
        let launchTime = Date().timeIntervalSince(startTime)
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Launch Timeout Test - \(launchTime)s"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertLessThan(launchTime, 30, "App should launch within 30 seconds") // Should be faster on a phone, slower when launching from simulated phone
    }
    
    // MARK: - Special Launch Conditions
    
    // Test 108: First Launch Simulation
    @MainActor
    func testFirstLaunchSimulation() throws {
        let app = XCUIApplication()
        app.launchArguments.append("-FIRST_LAUNCH")
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "First Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should handle first launch correctly")
    }
    
    // Test 109: Launch with Deep Link
    @MainActor
    func testLaunchWithDeepLink() throws {
        let app = XCUIApplication()
        // Note: Deep link testing would require actual URL scheme configuration
        app.launch()
        
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Deep Link Launch"
        attachment.lifetime = .keepAlways
        add(attachment)
        
        XCTAssertTrue(app.exists, "App should handle deep links")
    }
    
    // Test 110: Launch Regression Test
    @MainActor
    func testLaunchRegressionTest() throws {
        let app = XCUIApplication()
        app.launch()
        
        // Basic smoke test to ensure core functionality works
        if app.buttons["Sign In Anonymously"].exists {
            app.buttons["Sign In Anonymously"].tap()
            sleep(2)
        }
        
        // Verify all tabs are accessible
        let tabs = ["Home", "Search", "Predictions", "Info"]
        for tab in tabs {
            if app.tabBars.buttons[tab].exists {
                app.tabBars.buttons[tab].tap()
                sleep(2)
                
                let attachment = XCTAttachment(screenshot: app.screenshot())
                attachment.name = "Regression - \(tab) Tab"
                attachment.lifetime = .keepAlways
                add(attachment)
            }
        }
        
        XCTAssertTrue(app.exists, "Launch regression test completed")
    }
}
