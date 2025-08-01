//
//  HomeView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct HomeView: View {
    @StateObject private var viewModel = HomeViewModel()
    @EnvironmentObject var authService: AuthService
    @State private var selectedTimeframe: TimeFrame = .oneWeek
    @State private var selectedBet: BetWithGameInfo?
    @State private var showingBetSlip = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView("Loading your data...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .padding()
                } else if let errorMessage = viewModel.errorMessage {
                    ErrorView(
                        title: "Error Loading Data",
                        message: errorMessage,
                        retryAction: { viewModel.refreshData() }
                    )
                } else {
                    VStack(spacing: 20) {
                        // Portfolio Performance Chart
                        PortfolioChartView(
                            chartData: viewModel.chartData,
                            totalPnL: viewModel.totalPnL,
                            totalPnLFormatted: viewModel.totalPnLFormatted,
                            roiFormatted: viewModel.roiFormatted,
                            selectedTimeframe: $selectedTimeframe,
                            onTimeframeChange: { timeframe in
                                viewModel.updateChartData(for: timeframe)
                            }
                        )
                        
                        // Quick Actions
                        QuickActionsView()
                        
                        // Tracked Bets Section
                        TrackedBetsSectionView(
                            trackedBets: viewModel.trackedBets,
                            onBetTap: { bet in
                                selectedBet = bet
                                showingBetSlip = true
                            }
                        )
                        
                        // Historical Bets Section
                        HistoricalBetsSectionView(
                            recentBets: viewModel.recentBets,
                            onBetTap: { bet in
                                selectedBet = bet
                                showingBetSlip = true
                            }
                        )
                    }
                    .padding()
                }
            }
            .navigationTitle("Home")
            .sheet(isPresented: $showingBetSlip) {
                if let selectedBet = selectedBet {
                    TrackedBetSlipView(bet: selectedBet.bet) {
                        deleteBet(selectedBet)
                    }
                }
            }
            .refreshable {
                viewModel.refreshData()
            }
        }
        .onAppear {
            viewModel.loadData()
        }
    }
    
    // MARK: - Delete Bet Function
    private func deleteBet(_ betWithGameInfo: BetWithGameInfo) {
        Task {
            await viewModel.deleteBet(betWithGameInfo)
        }
    }
}

// MARK: - Error View Component
struct ErrorView: View {
    let title: String
    let message: String
    let retryAction: () -> Void
    
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundColor(.orange)
            
            Text(title)
                .font(.headline)
            
            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            Button("Try Again") {
                retryAction()
            }
            .buttonStyle(.bordered)
        }
        .padding()
    }
}

#Preview {
    HomeView()
        .environmentObject(AuthService())
}
