//
//  BetHistoryRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct DetailedBetHistoryRowView: View {
    let bet: BetWithGameInfo
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 12) {
                // Header with date and result
                HStack {
                    Text(bet.formattedGameDate)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Spacer()
                    
                    HStack(spacing: 6) {
                        Circle()
                            .fill(resultColor(for: bet.bet.result))
                            .frame(width: 8, height: 8)
                        
                        Text(bet.bet.result.rawValue.capitalized)
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(resultColor(for: bet.bet.result))
                    }
                }
                
                // Game and bet info
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(bet.gameMatchup)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.blue)
                        
                        Text(bet.bet.selection)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
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
                            
                            Circle()
                                .fill(Color(.systemGray4))
                                .frame(width: 3, height: 3)
                            
                            Text(formatOdds(bet.bet.odds))
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 8) {
                        if bet.bet.result != .pending {
                            Text(pnlText(for: bet.bet))
                                .font(.title3)
                                .fontWeight(.bold)
                                .foregroundColor(bet.bet.result == .won ? .green :
                                               bet.bet.result == .lost ? .red : .gray)
                        } else {
                            Text("Pending")
                                .font(.subheadline)
                                .foregroundColor(.orange)
                        }
                        
                        Image(systemName: "chevron.right")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(12)
            .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func resultColor(for result: BetResult) -> Color {
        switch result {
        case .won: return .green
        case .lost: return .red
        case .push: return .gray
        case .pending: return .orange
        }
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
            let winnings: Double
            if bet.odds > 0 {
                winnings = bet.amount * (bet.odds / 100)
            } else {
                winnings = bet.amount * (100 / abs(bet.odds))
            }
            return "+$\(Int(winnings))"
        case .lost:
            return "-$\(Int(bet.amount))"
        case .push:
            return "$0"
        case .pending:
            return "Pending"
        }
    }
}
