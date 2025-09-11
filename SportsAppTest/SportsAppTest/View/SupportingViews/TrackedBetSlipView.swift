//
//  TrackedBetSlipView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/27/25.
//


import SwiftUI

struct TrackedBetSlipView: View {
    let bet: Bet
    let onDelete: () -> Void
    @Environment(\.dismiss) var dismiss
    @State private var showingDeleteAlert = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Bet Header
                    betHeaderSection
                    
                    // Bet Details Card
                    betDetailsCard
                    
                    // Status Section
                    statusSection
                    
                    // Potential Payout
                    payoutSection
                    
                    // Delete Button
                    deleteButton
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Bet Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") {
                        dismiss()
                    }
                }
            }
            .alert("Delete Bet", isPresented: $showingDeleteAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Delete", role: .destructive) {
                    onDelete()
                    dismiss()
                }
            } message: {
                Text("Are you sure you want to delete this tracked bet? This action cannot be undone.")
            }
        }
    }
    
    // MARK: - Bet Header Section
    private var betHeaderSection: some View {
        VStack(spacing: 12) {
            // Bet Type Badge
            HStack {
                Text(bet.type.displayName)
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(betTypeColor(for: bet.type))
                    .cornerRadius(16)
                
                Spacer()
                
                // Status Indicator
                HStack(spacing: 6) {
                    Circle()
                        .fill(statusColor(for: bet.result))
                        .frame(width: 8, height: 8)
                    
                    Text(bet.result.rawValue.capitalized)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(statusColor(for: bet.result))
                }
            }
            
            // Selection
            Text(bet.selection)
                .font(.title2)
                .fontWeight(.bold)
                .multilineTextAlignment(.center)
            
            // Date placed
            Text("Placed on \(bet.placedAt.formatted(date: .abbreviated, time: .shortened))")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Bet Details Card
    private var betDetailsCard: some View {
        VStack(spacing: 16) {
            // Amount and Odds
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Wager Amount")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text("$\(formatCurrency(bet.amount))")
                        .font(.title3)
                        .fontWeight(.bold)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Odds")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text(formatOdds(bet.odds))
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                }
            }
            
            Divider()
            
            // Game ID Info (if you want to show which game this is for)
            HStack {
                Text("Game ID")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)
                
                Spacer()
                
                Text(String(bet.gameID.prefix(8)).uppercased())
                    .font(.caption)
                    .fontWeight(.medium)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Status Section
    private var statusSection: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: statusIcon(for: bet.result))
                    .font(.title2)
                    .foregroundColor(statusColor(for: bet.result))
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Bet Status")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text(statusDescription(for: bet.result))
                        .font(.subheadline)
                        .fontWeight(.medium)
                }
                
                Spacer()
            }
            
            if bet.result == .pending {
                Text("Your bet is being tracked. Check back after the game completes for results.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.leading)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Payout Section
    private var payoutSection: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Potential Payout")
                    .font(.headline)
                    .fontWeight(.semibold)
                
                Spacer()
            }
            
            HStack {
                VStack(alignment: .leading, spacing: 8) {
                    Text("To Win")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text("$\(formatCurrency(calculatePotentialWin()))")
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 8) {
                    Text("Total Payout")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text("$\(formatCurrency(calculateTotalPayout()))")
                        .font(.title3)
                        .fontWeight(.bold)
                }
            }
            
            // Show actual result if bet is settled
            if bet.result != .pending {
                Divider()
                
                HStack {
                    Text("Actual Result")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text(actualResultText())
                        .font(.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(actualResultColor())
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Delete Button
    private var deleteButton: some View {
        Button(action: {
            showingDeleteAlert = true
        }) {
            HStack {
                Image(systemName: "trash")
                Text("Delete Bet")
            }
            .font(.headline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.red)
            .cornerRadius(12)
        }
    }
    
    // MARK: - Helper Functions
    private func betTypeColor(for betType: BetType) -> Color {
        switch betType {
        case .moneyline:
            return .green
        case .spread:
            return .blue
        case .total:
            return .orange
        }
    }
    
    private func statusColor(for result: BetResult) -> Color {
        switch result {
        case .pending:
            return .orange
        case .won:
            return .green
        case .lost:
            return .red
        case .push:
            return .gray
        }
    }
    
    private func statusIcon(for result: BetResult) -> String {
        switch result {
        case .pending:
            return "clock"
        case .won:
            return "checkmark.circle.fill"
        case .lost:
            return "xmark.circle.fill"
        case .push:
            return "minus.circle.fill"
        }
    }
    
    private func statusDescription(for result: BetResult) -> String {
        switch result {
        case .pending:
            return "Pending Game Result"
        case .won:
            return "Bet Won!"
        case .lost:
            return "Bet Lost"
        case .push:
            return "Push (Tie)"
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func formatCurrency(_ amount: Double) -> String {
        return String(format: "%.2f", amount)
    }
    
    private func calculatePotentialWin() -> Double {
        if bet.odds > 0 {
            return bet.amount * (bet.odds / 100)
        } else {
            return bet.amount * (100 / abs(bet.odds))
        }
    }
    
    private func calculateTotalPayout() -> Double {
        return bet.amount + calculatePotentialWin()
    }
    
    private func actualResultText() -> String {
        switch bet.result {
        case .won:
            return "+$\(formatCurrency(calculatePotentialWin()))"
        case .lost:
            return "-$\(formatCurrency(bet.amount))"
        case .push:
            return "$0.00"
        case .pending:
            return "Pending"
        }
    }
    
    private func actualResultColor() -> Color {
        switch bet.result {
        case .won:
            return .green
        case .lost:
            return .red
        case .push:
            return .gray
        case .pending:
            return .orange
        }
    }
}

#Preview {
    TrackedBetSlipView(
        bet: Bet(
            id: "preview",
            userID: "user123",
            gameID: "game456",
            type: .moneyline,
            selection: "UNC ML",
            odds: 130,
            amount: 325.0,
            result: .pending,
            placedAt: Date()
        ),
        onDelete: {}
    )
}
