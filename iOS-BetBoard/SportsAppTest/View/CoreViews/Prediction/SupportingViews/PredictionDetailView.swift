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
                
                // BetSlip UI with amount tracking
                BetSlipUI(betSlip: prediction.betSlip) { betType, selection, odds, amount in
                    trackSpecificBet(betType: betType, selection: selection, odds: odds, amount: amount)
                }
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
