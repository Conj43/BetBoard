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

// MARK: - Header View
struct PredictionHeaderView: View {
    let predictionsCount: Int
    
    var body: some View {
        VStack(spacing: 4) {
            HStack {
                Text("Recommended Bets")
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Spacer()
                
                Text("\(predictionsCount) Bets")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            .padding(.top, 16)
            .padding(.bottom, 8)
            
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color.gray.opacity(0.2))
        }
        .background(Color(.systemBackground))
    }
}

// MARK: - Empty State View
struct PredictionEmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.bar")
                .font(.system(size: 50))
                .foregroundColor(.gray.opacity(0.6))
            
            Text("No Recommended Bets")
                .font(.headline)
            
            Text("Check back later for new betting recommendations.")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.vertical, 60)
        .frame(maxWidth: .infinity)
    }
}
