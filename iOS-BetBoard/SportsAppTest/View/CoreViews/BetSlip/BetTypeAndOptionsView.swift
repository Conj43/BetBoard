//
//  BetTypeAndOptionsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to remove moneyline options

import SwiftUI

struct BetTypeAndOptionsView: View {
    @Binding var selectedBetType: BetType
    let currentBettingLines: BettingLines
    @Binding var selectedBet: (String, Double)?
    var onBetAmountChange: () -> Void
    
    var body: some View {
        VStack(spacing: 16) {
            // Bet type selector - Only show supported bet types
            HStack(spacing: 0) {
                ForEach(BetType.supportedTypes, id: \.self) { betType in
                    Button(action: {
                        if selectedBetType != betType {
                            selectedBetType = betType
                            selectedBet = nil
                            onBetAmountChange()
                        }
                    }) {
                        Text(betType.displayName)
                            .font(.subheadline.bold())
                            .padding(.vertical, 12)
                            .frame(maxWidth: .infinity)
                            .background(selectedBetType == betType ? Color.blue : Color.gray.opacity(0.1))
                            .foregroundColor(selectedBetType == betType ? .white : .primary)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .background(Color.gray.opacity(0.1))
            .cornerRadius(8)
            
            // Bet options based on selected type
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 12) {
                    switch selectedBetType {
                    case .spread:
                        ForEach(currentBettingLines.spread.sorted(by: { $0.key < $1.key }), id: \.key) { key, odds in
                            BetOptionRow(
                                label: key,
                                odds: odds,
                                isSelected: selectedBet?.0 == key,
                                onSelect: {
                                    selectedBet = (key, odds)
                                    onBetAmountChange()
                                }
                            )
                        }
                    case .total:
                        ForEach(currentBettingLines.total.sorted(by: { $0.key < $1.key }), id: \.key) { key, odds in
                            BetOptionRow(
                                label: key,
                                odds: odds,
                                isSelected: selectedBet?.0 == key,
                                onSelect: {
                                    selectedBet = (key, odds)
                                    onBetAmountChange()
                                }
                            )
                        }
                    case .moneyline:
                        // This case should never be hit as we're using BetType.supportedTypes
                        Text("Moneyline betting is no longer supported")
                            .padding()
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.vertical, 8)
            }
            .frame(maxHeight: 200)
        }
    }
}

// BetOptionRow component
struct BetOptionRow: View {
    let label: String
    let odds: Double
    let isSelected: Bool
    let onSelect: () -> Void
    
    private var formattedOdds: String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    var body: some View {
        Button(action: onSelect) {
            HStack {
                Text(label)
                    .fontWeight(.medium)
                
                Spacer()
                
                Text(formattedOdds)
                    .fontWeight(.bold)
                    .foregroundColor(odds > 0 ? .green : .red)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.blue.opacity(0.1) : Color.gray.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 2)
                    )
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}
