//
//  BetHistoryView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI

struct BetHistoryView: View {
    @StateObject private var viewModel = BetHistoryViewModel()
    @EnvironmentObject var authService: AuthService
    @State private var selectedBet: BetWithGameInfo?
    @State private var showingBetSlip = false
    @State private var selectedFilter: BetResultFilter = .all
    @State private var selectedSort: SortOption = .dateNewest
    
    var body: some View {
        VStack(spacing: 0) {
            // Filters and Sort
            filtersSection
            
            if viewModel.isLoading {
                ProgressView("Loading bet history...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let errorMessage = viewModel.errorMessage {
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundColor(.orange)
                    
                    Text("Error Loading History")
                        .font(.headline)
                    
                    Text(errorMessage)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    
                    Button("Try Again") {
                        Task {
                            await viewModel.loadBetHistory()
                        }
                    }
                    .buttonStyle(.bordered)
                }
                .padding()
            } else if viewModel.filteredBets.isEmpty {
                BetHistoryEmptyStateView()
            } else {
                // Stats Summary
                statsSection
                
                // Bet List
                betListSection
            }
        }
        .navigationTitle("Bet History")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showingBetSlip) {
            if let selectedBet = selectedBet {
                TrackedBetSlipView(bet: selectedBet.bet) {
                    deleteBet(selectedBet)
                }
            }
        }
        .task {
            await viewModel.loadBetHistory()
        }
        .refreshable {
            await viewModel.loadBetHistory()
        }
        .onChange(of: selectedFilter) { _ in
            viewModel.applyFilters(filter: selectedFilter, sort: selectedSort)
        }
        .onChange(of: selectedSort) { _ in
            viewModel.applyFilters(filter: selectedFilter, sort: selectedSort)
        }
    }
    
    // MARK: - Filters Section
    private var filtersSection: some View {
        VStack(spacing: 12) {
            // Result Filter
            HStack {
                Text("Filter:")
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Picker("Filter", selection: $selectedFilter) {
                    ForEach(BetResultFilter.allCases, id: \.self) { filter in
                        Text(filter.displayName).tag(filter)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
            }
            
            // Sort Options
            HStack {
                Text("Sort:")
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Spacer()
                
                Picker("Sort", selection: $selectedSort) {
                    ForEach(SortOption.allCases, id: \.self) { sort in
                        Text(sort.displayName).tag(sort)
                    }
                }
                .pickerStyle(MenuPickerStyle())
            }
        }
        .padding()
        .background(Color(.systemGroupedBackground))
    }
    
    // MARK: - Stats Section
    private var statsSection: some View {
        VStack(spacing: 16) {
            HStack {
                Text("Summary")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
            }
            
            HStack(spacing: 16) {
                // Total Bets
                VStack(spacing: 4) {
                    Text("\(viewModel.totalBets)")
                        .font(.title2)
                        .fontWeight(.bold)
                    Text("Total Bets")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                
                // Win Rate
                VStack(spacing: 4) {
                    Text(viewModel.winRateFormatted)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(viewModel.winRate >= 50 ? .green : .red)
                    Text("Win Rate")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                
                // Total P&L
                VStack(spacing: 4) {
                    Text(viewModel.totalPnLFormatted)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(viewModel.totalPnL >= 0 ? .green : .red)
                    Text("Total P&L")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(12)
        }
        .padding(.horizontal)
    }
    
    // MARK: - Bet List Section
    private var betListSection: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(viewModel.filteredBets) { bet in
                    DetailedBetHistoryRowView(bet: bet) {
                        selectedBet = bet
                        showingBetSlip = true
                    }
                }
            }
            .padding(.horizontal)
        }
    }
    
    // MARK: - Empty State View
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "clock")
                .font(.system(size: 50))
                .foregroundColor(.secondary)
            
            Text("No Bet History")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Track some bets to see your history here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    // MARK: - Delete Bet Function
    private func deleteBet(_ betWithGameInfo: BetWithGameInfo) {
        Task {
            await viewModel.deleteBet(betWithGameInfo)
        }
    }
}
