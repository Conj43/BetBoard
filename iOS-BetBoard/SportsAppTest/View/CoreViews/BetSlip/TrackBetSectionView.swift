//
//  TrackBetSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//

import SwiftUI

struct TrackBetSectionView: View {
    let selection: String
    let odds: Double
    let selectedBetType: BetType
    let selectedSportsbook: Sportsbook
    @Binding var betAmount: String
    var onTrackBet: ((BetType, String, Double, Double) -> Void)?
    
    @State private var showingValidationError = false
    @State private var validationErrorMessage = ""
    
    var body: some View {
        VStack(spacing: 16) {
            // Bet Summary
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Tracking Bet")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("\(selection) @ \(formatOdds(odds))")
                        .font(.subheadline)
                        .fontWeight(.medium)
                }
                
                Spacer()
                
                HStack(spacing: 8) {
                    Image(systemName: "sportscourt")
                        .foregroundColor(.purple)
                    
                    Text(selectedSportsbook.displayName)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            
            // Custom Bet Amount Input (inline implementation)
            VStack(spacing: 8) {
                HStack {
                    Text("Amount")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Spacer()
                    
                    if let amount = Double(betAmount.replacingOccurrences(of: ",", with: "")), amount > 0 {
                        Text(potentialWinText(for: amount))
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }
                
                HStack {
                    Text("$")
                        .foregroundColor(.secondary)
                    
                    TextField("0", text: $betAmount)
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(8)
            }
            
            // Validation Error (if any)
            if showingValidationError {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.red)
                    
                    Text(validationErrorMessage)
                        .font(.caption)
                        .foregroundColor(.red)
                    
                    Spacer()
                }
                .padding(.horizontal)
            }
            
            // Track Button
            Button(action: trackBet) {
                Text("Track Bet")
                    .font(.headline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .cornerRadius(12)
            }
        }
        .padding()
    }
    
    private func trackBet() {
        showingValidationError = false
        
        guard let amount = Double(betAmount.replacingOccurrences(of: ",", with: "")) else {
            validationErrorMessage = "Please enter a valid amount"
            showingValidationError = true
            return
        }
        
        guard amount > 0 else {
            validationErrorMessage = "Amount must be greater than $0"
            showingValidationError = true
            return
        }
        
        onTrackBet?(selectedBetType, selection, odds, amount)
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func potentialWinText(for amount: Double) -> String {
        let winnings: Double
        
        if odds > 0 {
            // Positive American odds (e.g. +150)
            winnings = amount * (odds / 100.0)
        } else {
            // Negative American odds (e.g. -110)
            winnings = amount * (100.0 / abs(odds))
        }
        
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        
        return "To Win: \(formatter.string(from: NSNumber(value: winnings)) ?? "$0")"
    }
}

#Preview {
    TrackBetSectionView(
        selection: "UNC -5.5",
        odds: -110,
        selectedBetType: .spread,
        selectedSportsbook: .draftkings,
        betAmount: .constant("50")
    ) { betType, selection, odds, amount in
        print("Tracked bet: \(betType) \(selection) @ \(odds) for $\(amount)")
    }
}
