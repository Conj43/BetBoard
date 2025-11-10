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
                        spreadPredictionView(bet: bet)
                    } else {
                        fallbackView()
                    }
                case .total:
                    if let bet = prediction.totalBet {
                        totalPredictionView(bet: bet)
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
    
    // Spread prediction view
    private func spreadPredictionView(bet: String) -> some View {
        // Improved parsing logic to correctly separate team name from spread value
        let teamName: String
        let spreadValue: String
        
        // Find the index of the first + or - character which should mark the start of the spread value
        if let rangeOfPlus = bet.range(of: "+"), let rangeOfMinus = bet.range(of: "-") {
            // Both + and - exist, use the one that comes first
            let spreadStartIndex = min(rangeOfPlus.lowerBound, rangeOfMinus.lowerBound)
            teamName = String(bet[..<spreadStartIndex]).trimmingCharacters(in: .whitespaces)
            spreadValue = String(bet[spreadStartIndex...])
        } else if let rangeOfPlus = bet.range(of: "+") {
            // Only + exists
            teamName = String(bet[..<rangeOfPlus.lowerBound]).trimmingCharacters(in: .whitespaces)
            spreadValue = String(bet[rangeOfPlus.lowerBound...])
        } else if let rangeOfMinus = bet.range(of: "-") {
            // Only - exists
            teamName = String(bet[..<rangeOfMinus.lowerBound]).trimmingCharacters(in: .whitespaces)
            spreadValue = String(bet[rangeOfMinus.lowerBound...])
        } else {
            // No + or - found, use the entire string as the team name
            teamName = bet
            spreadValue = ""
        }
        
        let formattedTeamName = TeamNameFormatter.formatTeamName(teamName)
        
        return VStack(alignment: .leading, spacing: 4) {
            Text("Our Pick:")
                .font(.caption)
                .foregroundColor(.secondary)
            
            Text(formattedTeamName)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.purple)
            
            Text("Our Predicted Spread:")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.top, 8)
            
            Text(spreadValue)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.purple)
        }
    }
    
    // Total prediction view
    private func totalPredictionView(bet: String) -> some View {
        // Parse OVER/UNDER from the total value
        let overUnder: String
        let totalValue: String
        
        if bet.uppercased().contains("OVER") {
            overUnder = "OVER"
            let startIndex = bet.uppercased().range(of: "OVER")!.upperBound
            let remainder = bet[startIndex...].trimmingCharacters(in: .whitespaces)
            totalValue = remainder
        } else if bet.uppercased().contains("UNDER") {
            overUnder = "UNDER"
            let startIndex = bet.uppercased().range(of: "UNDER")!.upperBound
            let remainder = bet[startIndex...].trimmingCharacters(in: .whitespaces)
            totalValue = remainder
        } else {
            // If no OVER/UNDER found, use entire string as the total value
            overUnder = ""
            totalValue = bet
        }
        
        return VStack(alignment: .leading, spacing: 4) {
            Text("Our Pick:")
                .font(.caption)
                .foregroundColor(.secondary)
            
            Text(overUnder)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.purple)
            
            Text("Our Predicted Total:")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.top, 8)
            
            Text(totalValue)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.purple)
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
