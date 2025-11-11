//
//  BetTypeAndOptionsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.

import SwiftUI

struct BetTypeAndOptionsView: View {
    @Binding var selectedBetType: BetType
    let currentBettingLines: BettingLines
    @Binding var selectedBet: (String, Double)?
    var onBetAmountChange: () -> Void
    
    // Define the order of bet types to display
    private var orderedBetTypes: [BetType] {
        return [.moneyline, .spread, .total]
    }
    
    var body: some View {
        VStack(spacing: 16) {
            // Bet type selector with custom order
            HStack(spacing: 0) {
                ForEach(orderedBetTypes, id: \.self) { betType in
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
                        case .moneyline:
                            // Display moneyline options
                            if currentBettingLines.moneyline.isEmpty {
                                Text("No moneyline odds available for this game")
                                    .padding()
                                    .foregroundColor(.secondary)
                            } else {
                                ForEach(currentBettingLines.moneyline.sorted(by: { $0.key < $1.key }), id: \.key) { key, odds in
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
                            }
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
                    .foregroundColor(odds > 0 ? .green : .orange)
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
