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
                    userInfoSection
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
        .task {
            await viewModel.loadSettings()
        }
    }
    
    // MARK: - User Info Section
    private var userInfoSection: some View {
        HStack {
            // Profile Image Placeholder
            Circle()
                .fill(Color.blue.opacity(0.2))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(userInitials)
                        .font(.headline)
                        .fontWeight(.medium)
                        .foregroundColor(.blue)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(viewModel.settings?.userID.suffix(8).uppercased() ?? "User")
                    .font(.headline)
                    .fontWeight(.medium)
                
                Text("Anonymous User")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
        .padding(.vertical, 8)
    }
    
    private var userInitials: String {
        guard let userID = authService.currentUser?.uid else { return "U" }
        return String(userID.prefix(2)).uppercased()
    }
    
    // MARK: - Settings Section
    private var settingsSection: some View {
        Group {
            // Notifications Toggle
            HStack {
                Image(systemName: "bell")
                    .foregroundColor(.orange)
                    .frame(width: 25)
                
                Text("Notifications")
                
                Spacer()
                
                Toggle("", isOn: Binding(
                    get: { viewModel.settings?.notificationsEnabled ?? true },
                    set: { newValue in
                        Task {
                            await viewModel.updateNotifications(enabled: newValue)
                        }
                    }
                ))
            }
            
            // Dark Mode Toggle
            HStack {
                Image(systemName: "moon")
                    .foregroundColor(.purple)
                    .frame(width: 25)
                
                Text("Dark Mode")
                
                Spacer()
                
                Toggle("", isOn: Binding(
                    get: { viewModel.settings?.darkModeEnabled ?? false },
                    set: { newValue in
                        Task {
                            await viewModel.updateDarkMode(enabled: newValue)
                        }
                    }
                ))
            }
            
            // Odds Format Picker
            HStack {
                Image(systemName: "number")
                    .foregroundColor(.green)
                    .frame(width: 25)
                
                Text("Odds Format")
                
                Spacer()
                
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
                HStack {
                    Image(systemName: "info.circle")
                        .foregroundColor(.blue)
                        .frame(width: 25)
                    
                    Text("About BetBoard")
                }
            }
            
            NavigationLink(destination: HowItWorksView()) {
                HStack {
                    Image(systemName: "brain")
                        .foregroundColor(.purple)
                        .frame(width: 25)
                    
                    Text("How Predictions Work")
                }
            }
            
            HStack {
                Image(systemName: "number")
                    .foregroundColor(.gray)
                    .frame(width: 25)
                
                Text("Version")
                
                Spacer()
                
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
                HStack {
                    Image(systemName: "rectangle.portrait.and.arrow.right")
                        .foregroundColor(.red)
                        .frame(width: 25)
                    
                    Text("Sign Out")
                        .foregroundColor(.red)
                }
            }
        }
    }
}

// MARK: - App Info Detail View
struct AppInfoDetailView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // App Icon
                VStack(spacing: 16) {
                    Image(systemName: "chart.bar.xaxis")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)
                    
                    Text("BetBoard")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    Text("Version 1.0.0")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.bottom)
                
                // App Description
                VStack(alignment: .leading, spacing: 12) {
                    Text("What is BetBoard?")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("BetBoard is a sports betting analytics app that helps you make informed decisions by comparing odds across different sportsbooks and providing AI-powered predictions for college basketball games.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Divider()
                
                // Key Features
                VStack(alignment: .leading, spacing: 12) {
                    Text("Key Features")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    ForEach([
                        ("chart.bar.xaxis", "AI Predictions", "Get confidence-rated predictions for upcoming games"),
                        ("magnifyingglass", "Game Search", "Find games by team names and matchups"),
                        ("chart.line.uptrend.xyaxis", "Performance Tracking", "Track your betting performance over time"),
                        ("brain.head.profile", "Smart Analysis", "Detailed breakdowns of key factors for each game")
                    ], id: \.1) { icon, title, description in
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: icon)
                                .font(.title3)
                                .foregroundColor(.blue)
                                .frame(width: 25)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text(title)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                
                                Text(description)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                
                Divider()
                
                // Disclaimer
                VStack(alignment: .leading, spacing: 12) {
                    Text("Important Disclaimer")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("BetBoard is for informational and educational purposes only. We do not facilitate actual betting or gambling. All predictions are based on algorithmic analysis and should not be considered guaranteed outcomes. Please bet responsibly and within your means.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - How It Works View
struct HowItWorksView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                VStack(alignment: .leading, spacing: 12) {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 50))
                        .foregroundColor(.purple)
                    
                    Text("How Our AI Predictions Work")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Understanding the technology behind BetBoard's predictions")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .padding(.bottom)
                
                // How It Works Steps
                VStack(alignment: .leading, spacing: 20) {
                    ForEach([
                        ("1", "Data Collection", "We gather comprehensive data including team statistics, player performance, historical matchups, and current season trends."),
                        ("2", "Algorithm Analysis", "Our machine learning algorithms analyze multiple factors including offensive/defensive efficiency, pace of play, and situational performance."),
                        ("3", "Confidence Scoring", "Each prediction receives a confidence score from 0-100% based on the strength of the statistical indicators."),
                        ("4", "Line Comparison", "We compare our predictions against current sportsbook lines to identify potential value bets.")
                    ], id: \.0) { step, title, description in
                        HStack(alignment: .top, spacing: 16) {
                            Text(step)
                                .font(.title)
                                .fontWeight(.bold)
                                .foregroundColor(.purple)
                                .frame(width: 30)
                            
                            VStack(alignment: .leading, spacing: 8) {
                                Text(title)
                                    .font(.headline)
                                    .fontWeight(.semibold)
                                
                                Text(description)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                
                Divider()
                
                // Factors Considered
                VStack(alignment: .leading, spacing: 16) {
                    Text("Key Factors We Analyze")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 2), spacing: 12) {
                        ForEach([
                            "Team Records",
                            "Recent Performance",
                            "Head-to-Head History",
                            "Home/Away Splits",
                            "Conference Strength",
                            "Injury Reports",
                            "Pace of Play",
                            "Offensive Efficiency",
                            "Defensive Stats",
                            "Neutral Site Games"
                        ], id: \.self) { factor in
                            Text("• \(factor)")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                
                Divider()
                
                // Disclaimer
                VStack(alignment: .leading, spacing: 12) {
                    Text("Remember")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Our predictions are based on statistical analysis and machine learning, but sports can be unpredictable. Use our predictions as one tool in your decision-making process, not as guaranteed outcomes.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
        }
        .navigationTitle("How It Works")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    InfoView()
        .environmentObject(AuthService())
}
