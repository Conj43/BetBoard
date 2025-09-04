//
//  SearchView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI
import FirebaseAuth

struct SearchView: View {
    @StateObject private var viewModel = SearchViewModel()
    @EnvironmentObject var authService: AuthService
    
    var body: some View {
        NavigationView {
            VStack {
                // Search Bar
                searchBar
                
                // Content
                if viewModel.isLoading {
                    ProgressView("Loading games...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        
                        Text("Error Loading Games")
                            .font(.headline)
                        
                        Text(errorMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Button("Try Again") {
                            Task {
                                await viewModel.refreshData()
                            }
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                } else if viewModel.searchText.isEmpty {
                    emptyStateView
                } else if viewModel.searchResults.isEmpty {
                    noResultsView
                } else {
                    searchResultsList
                }
                
                Spacer()
            }
            .navigationTitle("Search")
            .refreshable {
                Task {
                    await viewModel.refreshData()
                }
            }
        }
    }
    
    // MARK: - Search Bar
    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.secondary)
            
            TextField("Search teams...", text: $viewModel.searchText)
                .textFieldStyle(PlainTextFieldStyle())
                .autocapitalization(.none)
                .disableAutocorrection(true)
            
            if !viewModel.searchText.isEmpty {
                Button(action: {
                    viewModel.clearSearch()
                }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .padding(.horizontal)
    }
    
    // MARK: - Empty State
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 50))
                .foregroundColor(.secondary)
            
            Text("Search for teams")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Start typing to find games and betting opportunities")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            // Popular searches hint
            VStack(alignment: .leading, spacing: 8) {
                Text("Popular searches:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                HStack {
                    ForEach(["Duke", "UNC", "Virginia"], id: \.self) { teamName in
                        Button(teamName) {
                            viewModel.searchText = teamName
                        }
                        .font(.caption)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.blue.opacity(0.1))
                        .foregroundColor(.blue)
                        .cornerRadius(16)
                    }
                }
            }
            .padding(.top)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    // MARK: - No Results View
    private var noResultsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 50))
                .foregroundColor(.secondary)
            
            Text("No results found")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Try searching for a different team name")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    // MARK: - Search Results List
    private var searchResultsList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(viewModel.searchResults) { betSlip in
                    NavigationLink(destination: BetSlipDetailView(betSlip: betSlip)) {
                        GameSearchResultRow(betSlip: betSlip)
                    }
                }
            }
            .padding(.horizontal)
        }
    }
}

// MARK: - Game Search Result Row
struct GameSearchResultRow: View {
    let betSlip: BetSlip
    
    var body: some View {
        HStack(spacing: 12) {
            // Away team info
            HStack(spacing: 8) {
                if let ranking = betSlip.awayTeam.ranking {
                    Text("#\(ranking)")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                }
                
                Text(betSlip.awayTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("(\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // @ symbol
            Text("@")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Home team info
            HStack(spacing: 8) {
                if let ranking = betSlip.homeTeam.ranking {
                    Text("#\(ranking)")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                }
                
                Text(betSlip.homeTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("(\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Game time and conference
            VStack(alignment: .trailing, spacing: 4) {
                Text(betSlip.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if betSlip.homeTeam.conference == betSlip.awayTeam.conference {
                    Text(betSlip.homeTeam.conference)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(4)
                }
            }
            
            // Chevron
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        .foregroundColor(.primary)
    }
}

// MARK: - Bet Slip Detail View
struct BetSlipDetailView: View {
    let betSlip: BetSlip
    @State private var showingTrackConfirmation = false
    @State private var trackedBetDetails: String = ""
    @State private var isTrackingBet = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                BetSlipUI(betSlip: betSlip) { betType, selection, odds, amount in
                    trackSelectedBet(betType: betType, selection: selection, odds: odds, amount: amount)
                }
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Game Details")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Bet Tracked!", isPresented: $showingTrackConfirmation) {
            Button("OK") { }
        } message: {
            Text("Successfully tracked: \(trackedBetDetails)")
        }
        .disabled(isTrackingBet)
    }
    
    private func trackSelectedBet(betType: BetType, selection: String, odds: Double, amount: Double) {
        trackedBetDetails = "\(selection) for $\(String(format: "%.2f", amount)) at \(formatOdds(odds))"
        isTrackingBet = true
        
        Task {
            await trackBetToFirebase(betType: betType, selection: selection, odds: odds, amount: amount)
        }
    }
    
    private func trackBetToFirebase(betType: BetType, selection: String, odds: Double, amount: Double) async {
        guard let currentUser = Auth.auth().currentUser else {
            await MainActor.run {
                isTrackingBet = false
            }
            return
        }
        
        let firebaseService = FirebaseService()
        let bet = Bet(
            id: UUID().uuidString,
            userID: currentUser.uid,
            gameID: betSlip.gameID,
            type: betType,
            selection: selection,
            odds: odds,
            amount: amount,
            result: .pending,
            placedAt: Date()
        )
        
        do {
            try await firebaseService.addUserBet(bet)
            await MainActor.run {
                isTrackingBet = false
                showingTrackConfirmation = true
            }
        } catch {
            // Handle error appropriately
            print("Failed to track bet: \(error)")
            await MainActor.run {
                isTrackingBet = false
                // You could show an error alert here
            }
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

#Preview {
    SearchView()
        .environmentObject(AuthService())
}
