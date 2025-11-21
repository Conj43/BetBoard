//
//  PredictionsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct PredictionsView: View {
    @StateObject private var viewModel = PredictionsViewModel()
    @EnvironmentObject var authService: AuthService
    @State private var showDatePicker = false
    @State private var showConferencePicker = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                if viewModel.isLoading {
                    ProgressView("Loading predictions...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    errorView(errorMessage: errorMessage)
                } else {
                    // Date Selector
                    dateSelector
                    
                    // View Mode Toggle
                    viewModeToggle
                    
                    // Filters (only show in All Games mode)
                    if viewModel.viewMode == .allGames {
                        filtersSection
                    }
                    
                    // Header
                    PredictionHeaderView(
                        predictionsCount: viewModel.filteredPredictions.count,
                        mode: viewModel.viewMode
                    )
                    
                    // Predictions List
                    predictionsList
                }
            }
            .background(Color(.systemGroupedBackground))
            .refreshable {
                Task {
                    await viewModel.refreshPredictions()
                }
            }
            .environmentObject(viewModel)
            .navigationTitle("Best Bets")
        }
        .preferredColorScheme(viewModel.colorScheme)
        .task {
            await viewModel.loadUserSettings()
            await viewModel.loadPredictions()
        }
    }
    
    // MARK: - Date Selector (Dropdown)
    private var dateSelector: some View {
        Button(action: {
            showDatePicker.toggle()
        }) {
            HStack {
                Image(systemName: "calendar")
                    .foregroundColor(.blue)
                
                Text(formattedSelectedDate)
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Image(systemName: "chevron.down")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.vertical, 12)
            .padding(.horizontal)
            .frame(maxWidth: .infinity)
            .background(Color(.systemBackground))
            .overlay(
                Rectangle()
                    .frame(height: 1)
                    .foregroundColor(Color.gray.opacity(0.2)),
                alignment: .bottom
            )
        }
        .sheet(isPresented: $showDatePicker) {
            DatePickerSheet(selectedDate: $viewModel.selectedDate, onDateSelected: {
                Task {
                    await viewModel.loadPredictions()
                }
            })
        }
    }
    
    // MARK: - View Mode Toggle
    private var viewModeToggle: some View {
        Picker("View Mode", selection: $viewModel.viewMode) {
            Text("Recommended").tag(PredictionsViewMode.recommended)
            Text("All Games").tag(PredictionsViewMode.allGames)
        }
        .pickerStyle(SegmentedPickerStyle())
        .padding(.horizontal)
        .padding(.vertical, 8)
        .onChange(of: viewModel.viewMode) {
            viewModel.switchViewMode(to: viewModel.viewMode)
        }
    }
    
    // MARK: - Filters Section
    private var filtersSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                // Conference Dropdown
                Menu {
                    Button("All Conferences") {
                        viewModel.updateConferenceFilter(.all)
                    }
                    
                    Divider()
                    
                    // All conferences from the JSON
                    ForEach(ConferenceFilter.allCases.dropFirst(), id: \.self) { conference in
                        Button(conference.rawValue) {
                            viewModel.updateConferenceFilter(conference)
                        }
                    }
                } label: {
                    HStack(spacing: 4) {
                        Text(viewModel.selectedConference == .all ? "Conference" : viewModel.selectedConference.rawValue)
                            .font(.subheadline)
                            .lineLimit(1)
                        Image(systemName: "chevron.down")
                            .font(.caption2)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color(.systemGray6))
                    .foregroundColor(.primary)
                    .cornerRadius(16)
                }
                
                Divider()
                    .frame(height: 20)
                
                // Ranking Filters
                ForEach([RankingFilter.all, .top25, .top50], id: \.self) { filter in
                    FilterChip(
                        title: filter.rawValue,
                        isSelected: viewModel.selectedRanking == filter
                    ) {
                        viewModel.updateRankingFilter(filter)
                    }
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 4)
        }
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color.gray.opacity(0.2)),
            alignment: .bottom
        )
    }
    
    private var formattedSelectedDate: String {
        let formatter = DateFormatter()
        if Calendar.current.isDateInToday(viewModel.selectedDate) {
            return "Today"
        } else if Calendar.current.isDateInYesterday(viewModel.selectedDate) {
            return "Yesterday"
        } else if Calendar.current.isDateInTomorrow(viewModel.selectedDate) {
            return "Tomorrow"
        } else {
            formatter.dateFormat = "EEE, MMM d"
            return formatter.string(from: viewModel.selectedDate)
        }
    }
    
    // MARK: - Error View
    private func errorView(errorMessage: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundColor(.orange)
            
            Text("Error Loading Predictions")
                .font(.headline)
            
            Text(errorMessage)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            Button("Try Again") {
                Task {
                    await viewModel.refreshPredictions()
                }
            }
            .buttonStyle(.bordered)
        }
        .padding()
    }
    
    // MARK: - Predictions List
    private var predictionsList: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                if viewModel.filteredPredictions.isEmpty {
                    PredictionEmptyStateView()
                } else {
                    ForEach(viewModel.filteredPredictions) { prediction in
                        NavigationLink(destination: PredictionDetailView(prediction: prediction, viewModel: viewModel)) {
                            PredictionRowView(prediction: prediction)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
            .padding(.horizontal)
            .padding(.top, 4)
        }
    }
}

// MARK: - Date Picker Sheet
struct DatePickerSheet: View {
    @Binding var selectedDate: Date
    let onDateSelected: () -> Void
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationView {
            VStack {
                DatePicker(
                    "Select Date",
                    selection: $selectedDate,
                    in: ...Date(),
                    displayedComponents: .date
                )
                .datePickerStyle(.graphical)
                .padding()
                
                Spacer()
            }
            .navigationTitle("Select Date")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        onDateSelected()
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

// MARK: - Filter Chip
struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline)
                .fontWeight(isSelected ? .semibold : .regular)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(isSelected ? Color.blue : Color(.systemGray6))
                .foregroundColor(isSelected ? .white : .primary)
                .cornerRadius(16)
        }
    }
}

// MARK: - Header View
struct PredictionHeaderView: View {
    let predictionsCount: Int
    let mode: PredictionsViewMode
    
    var body: some View {
        HStack {
            Text(mode == .recommended ? "Top Picks" : "All Games")
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(.primary)
            
            Spacer()
            
            Text("\(predictionsCount)")
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(.systemGroupedBackground))
    }
}

// MARK: - Empty State View
struct PredictionEmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.bar")
                .font(.system(size: 50))
                .foregroundColor(.gray.opacity(0.6))
            
            Text("No Games Available")
                .font(.headline)
            
            Text("Check back later for new games and predictions.")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.vertical, 60)
        .frame(maxWidth: .infinity)
    }
}
