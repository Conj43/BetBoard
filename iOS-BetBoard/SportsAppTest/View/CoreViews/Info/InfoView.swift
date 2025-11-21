//
//  InfoView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct InfoView: View {
    @StateObject private var viewModel = InfoViewModel()
    @EnvironmentObject var authService: AuthService
    @State private var showingSignOutAlert = false
    
    var body: some View {
        NavigationView {
            List {
                // User Info Section
                Section {
                    UserProfileSectionView(authService: authService, viewModel: viewModel)
                }
                
                // App Settings Section
                Section("Settings") {
                    if viewModel.isLoading {
                        ProgressView("Loading settings...")
                    } else {
                        settingsSection
                    }
                }
                
                // App Info Section
                Section("About") {
                    appInfoSection
                }
                
                // Account Section
                Section("Account") {
                    accountSection
                }
            }
            .navigationTitle("Info")
            .alert("Sign Out", isPresented: $showingSignOutAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Sign Out", role: .destructive) {
                    authService.signOut()
                }
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
        .preferredColorScheme(viewModel.colorScheme)
        .task {
            await viewModel.loadSettings()
        }
    }
    
    // MARK: - Settings Section
    private var settingsSection: some View {
        Group {
            // Notifications Toggle
            SettingsToggleView(
                icon: "bell",
                iconColor: .orange,
                title: "Notifications",
                isOn: Binding(
                    get: { viewModel.settings?.notificationsEnabled ?? true },
                    set: { newValue in
                        Task {
                            await viewModel.updateNotifications(enabled: newValue)
                        }
                    }
                )
            )
            
            // Dark Mode Toggle
            SettingsToggleView(
                icon: "moon",
                iconColor: .purple,
                title: "Dark Mode",
                isOn: Binding(
                    get: { viewModel.settings?.darkModeEnabled ?? false },
                    set: { newValue in
                        Task {
                            await viewModel.updateDarkMode(enabled: newValue)
                        }
                    }
                )
            )
            
            // Odds Format Picker
            SettingsRowView(
                icon: "number",
                iconColor: .green,
                title: "Odds Format"
            ) {
                Picker("Odds Format", selection: Binding(
                    get: { viewModel.settings?.preferredOddsFormat ?? .american },
                    set: { newValue in
                        Task {
                            await viewModel.updateOddsFormat(format: newValue)
                        }
                    }
                )) {
                    Text("American").tag(OddsFormat.american)
                    Text("Decimal").tag(OddsFormat.decimal)
                    Text("Fractional").tag(OddsFormat.fractional)
                }
                .pickerStyle(MenuPickerStyle())
            }
        }
    }
    
    // MARK: - App Info Section
    private var appInfoSection: some View {
        Group {
            NavigationLink(destination: AppInfoDetailView()) {
                SettingsRowView(
                    icon: "info.circle",
                    iconColor: .blue,
                    title: "About BetBoard"
                )
            }
            
            NavigationLink(destination: HowItWorksView()) {
                SettingsRowView(
                    icon: "brain",
                    iconColor: .purple,
                    title: "How Predictions Work"
                )
            }
            
            SettingsRowView(
                icon: "number",
                iconColor: .gray,
                title: "Version"
            ) {
                Text("1.0.0")
                    .foregroundColor(.secondary)
            }
        }
    }
    
    // MARK: - Account Section
    private var accountSection: some View {
        Group {
            Button(action: {
                showingSignOutAlert = true
            }) {
                SettingsRowView(
                    icon: "rectangle.portrait.and.arrow.right",
                    iconColor: .red,
                    title: "Sign Out",
                    titleColor: .red
                )
            }
        }
    }
}

#Preview {
    InfoView()
        .environmentObject(AuthService())
}
