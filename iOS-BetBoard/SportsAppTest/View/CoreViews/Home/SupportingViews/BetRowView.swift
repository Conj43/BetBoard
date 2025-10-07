//
//  BetRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.

import SwiftUI

// MARK: - Tracked Bet Row View
struct TrackedBetRowView: View {
    let bet: BetWithGameInfo
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 8) {
                // Game matchup header
                HStack {
                    Text(bet.gameMatchup)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text(bet.formattedGameDate)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Bet details
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(bet.bet.selection)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 8) {
                            Text(bet.bet.type.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Circle()
                                .fill(Color(.systemGray4))
                                .frame(width: 3, height: 3)
                            
                            Text("$\(Int(bet.bet.amount))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(formatOdds(bet.bet.odds))
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 6) {
                            Circle()
                                .fill(bet.bet.result == .pending ? Color.orange :
                                      bet.bet.result == .won ? Color.green :
                                      bet.bet.result == .lost ? Color.red : Color.gray)
                                .frame(width: 8, height: 8)
                            
                            Text(bet.bet.result.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

// MARK: - Historical Bet Row View
struct HistoricalBetRowView: View {
    let bet: BetWithGameInfo
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 8) {
                // Game matchup header
                HStack {
                    Text(bet.gameMatchup)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text(bet.formattedGameDate)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Bet details
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(bet.bet.selection)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 8) {
                            Text(bet.bet.type.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Circle()
                                .fill(Color(.systemGray4))
                                .frame(width: 3, height: 3)
                            
                            Text("$\(Int(bet.bet.amount))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(formatOdds(bet.bet.odds))
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        if bet.bet.result != .pending {
                            Text(pnlText(for: bet.bet))
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(bet.bet.result == .won ? .green :
                                               bet.bet.result == .lost ? .red : .gray)
                        } else {
                            HStack(spacing: 6) {
                                Circle()
                                    .fill(Color.orange)
                                    .frame(width: 8, height: 8)
                                
                                Text("Pending")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func pnlText(for bet: Bet) -> String {
        switch bet.result {
        case .won:
            // Calculate winnings based on odds
            let winnings: Double
            if bet.odds > 0 {
                // Positive odds: bet $100 to win $odds
                winnings = bet.amount * (bet.odds / 100)
            } else {
                // Negative odds: bet $odds to win $100
                winnings = bet.amount * (100 / abs(bet.odds))
            }
            return "+$\(Int(winnings))" // Show just the profit
        case .lost:
            return "-$\(Int(bet.amount))" // Show the amount lost
        case .push:
            return "$0"
        case .pending:
            return "Pending"
        }
    }
}
