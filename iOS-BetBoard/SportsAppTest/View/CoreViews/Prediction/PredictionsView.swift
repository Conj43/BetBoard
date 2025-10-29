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
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                if viewModel.isLoading {
                    ProgressView("Loading predictions...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    errorView(errorMessage: errorMessage)
                } else {
                    // Header Section
                    PredictionHeaderView(predictionsCount: viewModel.filteredPredictions.count)
                    
                    // Bet Type Filter
                    BetTypeFilterView(selectedBetType: $viewModel.selectedBetType)
                    
                    // Predictions List
                    predictionsList
                }
            }
            .navigationTitle("Predictions")
            .background(Color(.systemGroupedBackground))
            .refreshable {
                Task {
                    await viewModel.refreshPredictions()
                }
            }
            .environmentObject(viewModel) // Pass the viewModel as an environment object
        }
        .task {
            await viewModel.loadPredictions()
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
            LazyVStack(spacing: 12) {
                if viewModel.filteredPredictions.isEmpty {
                    PredictionEmptyStateView()
                } else {
                    ForEach(viewModel.filteredPredictions) { prediction in
                        NavigationLink(destination: PredictionDetailView(prediction: prediction, viewModel: viewModel)) {
                            PredictionRowView(prediction: prediction)
                                // We don't need to pass the view model here since it's in the environment
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
            .padding(.horizontal)
            .padding(.top, 8)
        }
    }
}
