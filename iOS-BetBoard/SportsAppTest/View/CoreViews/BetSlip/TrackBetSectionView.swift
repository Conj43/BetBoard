//
//  TrackBetSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


//
//  TrackBetSectionView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct TrackBetSectionView: View {
    let selection: String
    let odds: Double
    let selectedBetType: BetType
    let selectedSportsbook: Sportsbook
    @Binding var betAmount: String
    let onTrackBet: ((BetType, String, Double, Double) -> Void)?
    
    private var isTrackButtonEnabled: Bool {
        guard let amount = Double(betAmount) else { return false }
        return amount > 0
    }
    
    var body: some View {
        VStack(spacing: 12) {
            // Selected bet display
            selectedBetDisplay
            
            // Amount input section
            amountInputSection
            
            // Track bet button
            trackBetButton
        }
        .padding(.horizontal)
        .padding(.bottom)
    }
    
    // MARK: - Selected Bet Display
    private var selectedBetDisplay: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Selected Bet")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)
                
                Text(selection)
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                HStack(spacing: 4) {
                    Text(BetSlipHelpers.formatOdds(odds))
                        .font(.caption)
                        .foregroundColor(.blue)
                    
                    Text("(\(selectedSportsbook.displayName))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 4) {
                Text("Potential Payout")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)
                
                if let amount = Double(betAmount), amount > 0 {
                    let payout = BetSlipHelpers.calculatePayout(amount: amount, odds: odds)
                    Text("$\(String(format: "%.2f", payout))")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.green)
                    
                    Text("Profit: $\(String(format: "%.2f", payout - amount))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else {
                    Text("Enter amount")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
    
    // MARK: - Amount Input Section
    private var amountInputSection: some View {
        VStack(spacing: 8) {
            HStack {
                Text("Bet Amount")
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Spacer()
            }
            
            HStack {
                Text("$")
                    .font(.headline)
                    .foregroundColor(.secondary)
                
                TextField("0.00", text: $betAmount)
                    .keyboardType(.decimalPad)
                    .font(.headline)
                    .textFieldStyle(PlainTextFieldStyle())
                    .multilineTextAlignment(.trailing)
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(8)
            
            // Quick amount buttons
            HStack(spacing: 8) {
                ForEach([25, 50, 100, 250], id: \.self) { amount in
                    Button("$\(amount)") {
                        betAmount = String(amount)
                    }
                    .font(.caption)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.blue.opacity(0.1))
                    .foregroundColor(.blue)
                    .cornerRadius(6)
                }
                
                Spacer()
            }
        }
    }
    
    // MARK: - Track Bet Button
    private var trackBetButton: some View {
        Button(action: {
            if let amount = Double(betAmount), amount > 0 {
                onTrackBet?(selectedBetType, selection, odds, amount)
            }
        }) {
            HStack {
                Image(systemName: "plus.circle.fill")
                Text("Track This Bet")
            }
            .font(.headline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(isTrackButtonEnabled ? Color.blue : Color.gray)
            .cornerRadius(12)
        }
        .disabled(!isTrackButtonEnabled)
    }
}