//
//  BetTypeAndOptionsView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//

import SwiftUI

struct BetTypeAndOptionsView: View {
    @Binding var selectedBetType: BetType
    let currentBettingLines: BettingLines
    @Binding var selectedBet: (String, Double)?
    let onBetAmountChange: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            // Bet Type Selector
            betTypeSelector
            
            // Betting Options
            bettingOptionsSection
        }
    }
    
    // MARK: - Bet Type Selector
    private var betTypeSelector: some View {
        HStack(spacing: 0) {
            ForEach([BetType.moneyline, BetType.spread, BetType.total], id: \.self) { betType in
                Button(action: {
                    selectedBetType = betType
                    selectedBet = nil
                    onBetAmountChange()
                }) {
                    Text(betTypeDisplayName(betType))
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(selectedBetType == betType ? .white : .primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(selectedBetType == betType ? Color.blue : Color.clear)
                }
            }
        }
        .background(Color(.systemGray6))
        .cornerRadius(8)
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
    
    // MARK: - Betting Options Section
    private var bettingOptionsSection: some View {
        VStack(spacing: 8) {
            switch selectedBetType {
            case .moneyline:
                moneylineOptions
            case .spread:
                spreadOptions
            case .total:
                totalOptions
            }
        }
        .padding(.horizontal)
        .padding(.bottom)
    }
    
    private var moneylineOptions: some View {
        VStack(spacing: 8) {
            ForEach(Array(currentBettingLines.moneyline.keys.sorted()), id: \.self) { team in
                if let odds = currentBettingLines.moneyline[team] {
                    BetOptionRow(
                        selection: "\(team) ML",
                        odds: odds,
                        isSelected: selectedBet?.0 == "\(team) ML"
                    ) {
                        selectedBet = ("\(team) ML", odds)
                    }
                }
            }
        }
    }
    
    private var spreadOptions: some View {
        VStack(spacing: 8) {
            ForEach(Array(currentBettingLines.spread.keys.sorted()), id: \.self) { spread in
                if let odds = currentBettingLines.spread[spread] {
                    BetOptionRow(
                        selection: spread,
                        odds: odds,
                        isSelected: selectedBet?.0 == spread
                    ) {
                        selectedBet = (spread, odds)
                    }
                }
            }
        }
    }
    
    private var totalOptions: some View {
        VStack(spacing: 8) {
            ForEach(Array(currentBettingLines.total.keys.sorted()), id: \.self) { total in
                if let odds = currentBettingLines.total[total] {
                    BetOptionRow(
                        selection: total,
                        odds: odds,
                        isSelected: selectedBet?.0 == total
                    ) {
                        selectedBet = (total, odds)
                    }
                }
            }
        }
    }
    
    // MARK: - Helper
    private func betTypeDisplayName(_ betType: BetType) -> String {
        switch betType {
        case .moneyline: return "Moneyline"
        case .spread: return "Spread"
        case .total: return "Total"
        }
    }
}
