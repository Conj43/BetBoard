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
    var onBetAmountChange: () -> Void
    
    private var hasSpreadOptions: Bool {
        return !currentBettingLines.spread.isEmpty
    }
    
    private var hasMoneylineOptions: Bool {
        return !currentBettingLines.moneyline.isEmpty
    }
    
    private var hasTotalOptions: Bool {
        return !currentBettingLines.total.isEmpty
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Bet Type Selector
            HStack(spacing: 0) {
                ForEach([BetType.spread, BetType.moneyline, BetType.total], id: \.self) { betType in
                    Button {
                        // Only allow selecting types that have options
                        if shouldEnableBetType(betType) {
                            selectedBetType = betType
                            selectedBet = nil
                            onBetAmountChange()
                        }
                    } label: {
                        VStack {
                            Text(getBetTypeDisplayName(betType))
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(selectedBetType == betType ? Color.purple : Color(.systemGray6))
                        .foregroundColor(selectedBetType == betType ? .white : (shouldEnableBetType(betType) ? .primary : .gray))
                    }
                    .disabled(!shouldEnableBetType(betType))
                }
            }
            .background(Color(.systemGray6))
            
            // Divider
            Divider()
            
            // Bet Options
            VStack(spacing: 12) {
                switch selectedBetType {
                case .spread:
                    spreadOptionsView
                case .moneyline:
                    moneylineOptionsView
                case .total:
                    totalOptionsView
                }
            }
            .padding()
        }
    }
    
    private func getBetTypeDisplayName(_ betType: BetType) -> String {
        switch betType {
        case .spread:
            return "Spread"
        case .moneyline:
            return "Moneyline"
        case .total:
            return "Total"
        }
    }
    
    private func shouldEnableBetType(_ betType: BetType) -> Bool {
        switch betType {
        case .spread:
            return hasSpreadOptions
        case .moneyline:
            return hasMoneylineOptions
        case .total:
            return hasTotalOptions
        }
    }
    
    private var spreadOptionsView: some View {
        VStack(spacing: 8) {
            if hasSpreadOptions {
                ForEach(currentBettingLines.spread.sorted { $0.key < $1.key }, id: \.key) { key, value in
                    BetTypeOptionRow(
                        label: key,
                        value: formatOdds(value),
                        isSelected: selectedBet?.0 == key,
                        onSelect: {
                            selectedBet = (key, value)
                            onBetAmountChange()
                        }
                    )
                }
            } else {
                noBetsAvailableView()
            }
        }
    }
    
    private var moneylineOptionsView: some View {
        VStack(spacing: 8) {
            if hasMoneylineOptions {
                ForEach(currentBettingLines.moneyline.sorted { $0.key < $1.key }, id: \.key) { key, value in
                    BetTypeOptionRow(
                        label: key,
                        value: formatOdds(value),
                        isSelected: selectedBet?.0 == key,
                        onSelect: {
                            selectedBet = (key, value)
                            onBetAmountChange()
                        }
                    )
                }
            } else {
                noBetsAvailableView()
            }
        }
    }
    
    private var totalOptionsView: some View {
        VStack(spacing: 8) {
            if hasTotalOptions {
                ForEach(currentBettingLines.total.sorted { $0.key < $1.key }, id: \.key) { key, value in
                    BetTypeOptionRow(
                        label: key,
                        value: formatOdds(value),
                        isSelected: selectedBet?.0 == key,
                        onSelect: {
                            selectedBet = (key, value)
                            onBetAmountChange()
                        }
                    )
                }
            } else {
                noBetsAvailableView()
            }
        }
    }
    
    private func noBetsAvailableView() -> some View {
        Text("No betting lines available for this option")
            .font(.caption)
            .foregroundColor(.secondary)
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical)
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

// Renamed to avoid conflicts with BetOptionRow in BetOptionRow.swift
struct BetTypeOptionRow: View {
    let label: String
    let value: String
    let isSelected: Bool
    let onSelect: () -> Void
    
    private var formattedLabel: String {
            // For moneyline bets, the label is just the team name
            if !label.contains(" ") {
                return TeamNameFormatter.formatTeamName(label)
            }
            
            // For spread bets, format the team name but keep the spread
            let components = label.components(separatedBy: " ")
            if components.count >= 2 {
                let teamName = components[0]
                let spreadValue = components[1...].joined(separator: " ")
                return "\(TeamNameFormatter.formatTeamName(teamName)) \(spreadValue)"
            }
            
            return label
        }
    
    var body: some View {
        Button(action: onSelect) {
            HStack {
                Text(label)
                    .font(.subheadline)
                    .foregroundColor(.primary)
                
                Spacer()
                
                Text(value)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.blue)
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.blue.opacity(0.1) : Color(.systemGray6))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}
