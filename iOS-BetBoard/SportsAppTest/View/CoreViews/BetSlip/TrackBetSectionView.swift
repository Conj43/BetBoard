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
    
    // Add state variables for validation
    @State private var showingValidationError = false
    @State private var validationErrorMessage = ""
    @State private var showPotentialWinnings = true
    
    private var formattedOdds: String {
        return formatOdds(odds)
    }
    
    private var betAmountDouble: Double {
        return Double(betAmount.replacingOccurrences(of: ",", with: "")) ?? 0
    }
    
    private var isValidAmount: Bool {
        return betAmountDouble > 0
    }
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Track Bet")
                        .font(.headline)
                    
                    Text("\(selectedBetType.displayName): \(selection) (\(formattedOdds))")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                TextField("$", text: $betAmount)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 80)
                    .padding(8)
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(8)
            }
            
            // Show potential winnings if bet amount is valid
            if isValidAmount && showPotentialWinnings {
                HStack {
                    Spacer()
                    Text(potentialWinText(for: betAmountDouble))
                        .font(.caption)
                        .foregroundColor(.green)
                        .padding(.trailing, 4)
                }
            }
            
            Button(action: {
                trackBet()
            }) {
                Text("Track Bet")
                    .fontWeight(.bold)
                    .padding(.vertical, 12)
                    .frame(maxWidth: .infinity)
                    .background(isValidAmount ? Color.green : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
            .disabled(!isValidAmount)
        }
        .padding(16)
        .background(Color.gray.opacity(0.05))
        .alert(isPresented: $showingValidationError) {
            Alert(
                title: Text("Invalid Input"),
                message: Text(validationErrorMessage),
                dismissButton: .default(Text("OK"))
            )
        }
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
        
        // Note: We still pass the original selection to onTrackBet
        // since that's the format needed for database storage
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
