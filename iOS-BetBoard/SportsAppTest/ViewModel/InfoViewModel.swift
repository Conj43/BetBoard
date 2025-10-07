//
//  InfoViewModel.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  InfoViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import FirebaseAuth
import Combine

@MainActor
class InfoViewModel: ObservableObject {
    @Published var settings: AppSettings?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let firebaseService = FirebaseService()
    
    func loadSettings() async {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to view settings"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let userSettings = try await firebaseService.fetchUserSettings(for: currentUser.uid)
            
            await MainActor.run {
                self.settings = userSettings
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load settings: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    func updateNotifications(enabled: Bool) async {
        guard let currentSettings = settings else { return }
        
        let updatedSettings = AppSettings(
            userID: currentSettings.userID,
            notificationsEnabled: enabled,
            darkModeEnabled: currentSettings.darkModeEnabled,
            preferredOddsFormat: currentSettings.preferredOddsFormat
        )
        
        await updateSettings(updatedSettings)
    }
    
    func updateDarkMode(enabled: Bool) async {
        guard let currentSettings = settings else { return }
        
        let updatedSettings = AppSettings(
            userID: currentSettings.userID,
            notificationsEnabled: currentSettings.notificationsEnabled,
            darkModeEnabled: enabled,
            preferredOddsFormat: currentSettings.preferredOddsFormat
        )
        
        await updateSettings(updatedSettings)
    }
    
    func updateOddsFormat(format: OddsFormat) async {
        guard let currentSettings = settings else { return }
        
        let updatedSettings = AppSettings(
            userID: currentSettings.userID,
            notificationsEnabled: currentSettings.notificationsEnabled,
            darkModeEnabled: currentSettings.darkModeEnabled,
            preferredOddsFormat: format
        )
        
        await updateSettings(updatedSettings)
    }
    
    private func updateSettings(_ newSettings: AppSettings) async {
        do {
            try await firebaseService.updateUserSettings(newSettings)
            
            await MainActor.run {
                self.settings = newSettings
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to update settings: \(error.localizedDescription)"
            }
        }
    }
}