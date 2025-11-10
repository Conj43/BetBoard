//
//  PredictionSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//

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
        return (prediction.spreadBet != nil) || (prediction.totalBet != nil)
    }
    
    private var bestBetType: BetType {
        // Default to spread if both are available
        if prediction.spreadBet != nil {
            return .spread
        } else if prediction.totalBet != nil {
            return .total
        }
        return .spread
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
                
                // Bet type selector - only show spread and total
                Picker("Bet Type", selection: $selectedBetType) {
                    if prediction.spreadBet != nil {
                        Text("Spread").tag(BetType.spread)
                    }
                    if prediction.totalBet != nil {
                        Text("Total").tag(BetType.total)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.vertical, 4)
                
                // Show the selected bet type prediction
                switch selectedBetType {
                case .spread:
                    if let bet = prediction.spreadBet {
                        predictionView(betType: "Our Pick \nOur Predicted Spread", bet: bet, isSpread: true)
                    } else {
                        fallbackView()
                    }
                case .total:
                    if let bet = prediction.totalBet {
                        predictionView(betType: "Total", bet: bet)
                    } else {
                        fallbackView()
                    }
                case .moneyline:
                    // Should never reach here, but provide fallback just in case
                    fallbackView()
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
                // Default to the best available bet type
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
    
    // Simplified predictionView without confidence parameter
    private func predictionView(betType: String, bet: String, isSpread: Bool = false) -> some View {
        // Format the bet string based on bet type
        let formattedBet: String
        if betType.contains("Spread") || isSpread {
            // Process spread bet formatting
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
            
            Text("DK line")
                .font(.caption)
                .foregroundColor(.green)
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
