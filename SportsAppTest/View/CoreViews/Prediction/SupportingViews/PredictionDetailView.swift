//
//  PredictionDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  PredictionDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct PredictionDetailView: View {
    let prediction: PredictionGame
    @ObservedObject var viewModel: PredictionsViewModel
    @State private var showingTrackConfirmation = false
    @State private var trackingInProgress = false
    @State private var trackedBetDetails: String = ""
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Prediction Analysis Header
                predictionAnalysisHeader
                
                // BetSlip UI with amount tracking
                BetSlipUI(betSlip: prediction.betSlip) { betType, selection, odds, amount in
                    trackSpecificBet(betType: betType, selection: selection, odds: odds, amount: amount)
                }
                
                // Additional Analysis
                additionalAnalysisSection
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Prediction Details")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Bet Tracked!", isPresented: $showingTrackConfirmation) {
            Button("OK") { }
        } message: {
            Text("Successfully tracked: \(trackedBetDetails)")
        }
        .disabled(trackingInProgress)
    }
    
    private var predictionAnalysisHeader: some View {
        VStack(spacing: 16) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.purple)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Analysis")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Recommended Bet")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(Int(prediction.confidence))%")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.purple)
                    
                    Text("Confidence")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            if let analysis = prediction.analysis {
                Text(analysis)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.leading)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private var additionalAnalysisSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Key Factors")
                .font(.headline)
                .fontWeight(.semibold)
            
            ForEach(prediction.keyFactors, id: \.self) { factor in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundColor(.green)
                        .padding(.top, 2)
                    
                    Text(factor)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private func trackSpecificBet(betType: BetType, selection: String, odds: Double, amount: Double) {
        trackingInProgress = true
        trackedBetDetails = "\(selection) for $\(String(format: "%.2f", amount)) at \(formatOdds(odds))"
        
        Task {
            await viewModel.trackSpecificBet(
                from: prediction,
                betType: betType,
                selection: selection,
                odds: odds,
                amount: amount
            )
            
            await MainActor.run {
                trackingInProgress = false
                if viewModel.errorMessage == nil {
                    showingTrackConfirmation = true
                }
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