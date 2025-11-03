//
//  PredictionSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


import SwiftUI

struct PredictionSectionView: View {
    let prediction: PredictionInfo
    @State private var selectedBetType: BetType = .spread
    
    // Helper computed properties to safely access prediction data
    private var hasPredictions: Bool {
        return (prediction.moneylineBet != nil && prediction.moneylineConfidence > 0) ||
               (prediction.spreadBet != nil && prediction.spreadConfidence > 0) ||
               (prediction.totalBet != nil && prediction.totalConfidence > 0)
    }
    
    private var bestBetType: BetType {
        let confidences: [(type: BetType, confidence: Double)] = [
            (.moneyline, prediction.moneylineConfidence),
            (.spread, prediction.spreadConfidence),
            (.total, prediction.totalConfidence)
        ]
        
        return confidences.max(by: { $0.confidence < $1.confidence })?.type ?? .spread
    }
    
    var body: some View {
        if hasPredictions {
            VStack(alignment: .leading, spacing: 8) {
                // Header
                HStack {
                    Image(systemName: "brain.head.profile")
                        .foregroundColor(.purple)
                    Text("Our Predictions")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Spacer()
                }
                
                // Bet type selector
                Picker("Bet Type", selection: $selectedBetType) {
                    if prediction.spreadBet != nil && prediction.spreadConfidence > 0 {
                        Text("Spread").tag(BetType.spread)
                    }
                    if prediction.moneylineBet != nil && prediction.moneylineConfidence > 0 {
                        Text("Moneyline").tag(BetType.moneyline)
                    }
                    if prediction.totalBet != nil && prediction.totalConfidence > 0 {
                        Text("Total").tag(BetType.total)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.vertical, 4)
                
                // Show the selected bet type prediction
                switch selectedBetType {
                case .moneyline:
                    if let bet = prediction.moneylineBet, prediction.moneylineConfidence > 0 {
                        predictionView(betType: "Moneyline", bet: bet, confidence: prediction.moneylineConfidence)
                    } else {
                        fallbackView()
                    }
                case .spread:
                    if let bet = prediction.spreadBet, prediction.spreadConfidence > 0 {
                        predictionView(betType: "Spread", bet: bet, confidence: prediction.spreadConfidence)
                    } else {
                        fallbackView()
                    }
                case .total:
                    if let bet = prediction.totalBet, prediction.totalConfidence > 0 {
                        predictionView(betType: "Total", bet: bet, confidence: prediction.totalConfidence)
                    } else {
                        fallbackView()
                    }
                }
                
                // Analysis if available
                if let analysis = prediction.analysis {
                    Text(analysis)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }
            }
            .padding()
            .background(Color.purple.opacity(0.05))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.purple.opacity(0.2), lineWidth: 1)
            )
            .padding(.horizontal)
            .padding(.bottom)
            .onAppear {
                // Default to the bet type with highest confidence
                selectedBetType = bestBetType
            }
        } else {
            // Fallback if no predictions available
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "brain.head.profile")
                        .foregroundColor(.purple)
                    Text("No Predictions Available")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Spacer()
                }
                
                Text("We don't have specific predictions for this game yet.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color.purple.opacity(0.05))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.purple.opacity(0.2), lineWidth: 1)
            )
            .padding(.horizontal)
            .padding(.bottom)
        }
    }
    
    private func predictionView(betType: String, bet: String, confidence: Double) -> some View {
        // Format the bet string based on bet type
        let formattedBet: String
        if betType == "Moneyline" {
            formattedBet = TeamNameFormatter.formatTeamName(bet)
        } else if betType == "Spread" {
            let components = bet.components(separatedBy: " ")
            if components.count >= 2 {
                let teamName = components[0]
                let spreadValue = components[1...].joined(separator: " ")
                formattedBet = "\(TeamNameFormatter.formatTeamName(teamName)) \(spreadValue)"
            } else {
                formattedBet = bet
            }
        } else {
            formattedBet = bet
        }
        
        return HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(betType)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Text(formattedBet)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.purple)
            }
            
            Spacer()
            
            Text("\(Int(confidence))% to cover DK line")
                .font(.caption)
                .foregroundColor(confidence > 50 ? .green : .orange)
                .fontWeight(.semibold)
        }
    }
    
    private func fallbackView() -> some View {
        HStack {
            Text("Select another bet type with available predictions")
                .font(.caption)
                .italic()
                .foregroundColor(.secondary)
            Spacer()
        }
    }
}
