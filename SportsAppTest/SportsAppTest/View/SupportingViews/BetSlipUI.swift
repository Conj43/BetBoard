//
//  BetSlipUI.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct BetSlipUI: View {
    let betSlip: BetSlip
    @State private var selectedBetType: BetType = .spread
    @State private var selectedBet: (String, Double)?
    @State private var betAmount: String = ""
    @State private var showingAmountInput = false
    
    // Add callback for track bet action
    var onTrackBet: ((BetType, String, Double, Double) -> Void)?
    
    var body: some View {
        VStack(spacing: 0) {
            // Header with matchup and game info
            headerSection
            
            // Sportsbook info
            sportsbookSection
            
            // Bet type selector
            betTypeSelector
            
            // Betting options
            bettingOptionsSection
            
            // Prediction info (if available)
            if let predictionInfo = betSlip.predictionInfo {
                predictionSection(predictionInfo)
            }
            
            // Track Bet Button with Amount Input
            if let selectedBet = selectedBet {
                trackBetSection(selection: selectedBet.0, odds: selectedBet.1)
            }
        }
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Track Bet Section with Amount Input
    private func trackBetSection(selection: String, odds: Double) -> some View {
        VStack(spacing: 12) {
            // Selected bet display
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Selected Bet")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text(selection)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    
                    Text(formatOdds(odds))
                        .font(.caption)
                        .foregroundColor(.blue)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Potential Payout")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    if let amount = Double(betAmount), amount > 0 {
                        let payout = calculatePayout(amount: amount, odds: odds)
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
            
            // Amount input section
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
            
            // Track bet button
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
        .padding(.horizontal)
        .padding(.bottom)
    }
    
    private var isTrackButtonEnabled: Bool {
        guard let amount = Double(betAmount) else { return false }
        return amount > 0
    }
    
    private func calculatePayout(amount: Double, odds: Double) -> Double {
        if odds > 0 {
            return amount * (odds / 100) + amount
        } else {
            return amount * (100 / abs(odds)) + amount
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    // MARK: - Header Section
    private var headerSection: some View {
        VStack(spacing: 12) {
            // Game time
            Text(betSlip.formattedGameTime)
                .font(.caption)
                .foregroundColor(.secondary)
            
            // Matchup
            HStack(spacing: 20) {
                // Away team
                VStack(spacing: 8) {
                    // Team logo placeholder - implement later
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 40, height: 40)
                        .overlay(
                            Text(String(betSlip.awayTeam.shortName.prefix(3)))
                                .font(.caption)
                                .fontWeight(.bold)
                        )
                    
                    Text(betSlip.awayTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    
                    if let ranking = betSlip.awayTeam.ranking {
                        Text("#\(ranking)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    
                    Text("(\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // VS
                Text("@")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.secondary)
                
                // Home team
                VStack(spacing: 8) {
                    // Team logo placeholder - implement later
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 40, height: 40)
                        .overlay(
                            Text(String(betSlip.homeTeam.shortName.prefix(3)))
                                .font(.caption)
                                .fontWeight(.bold)
                        )
                    
                    Text(betSlip.homeTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    
                    if let ranking = betSlip.homeTeam.ranking {
                        Text("#\(ranking)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    
                    Text("(\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            // Neutral site indicator
            if betSlip.neutralSite {
                Text("Neutral Site")
                    .font(.caption)
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.1))
                    .cornerRadius(4)
            }
        }
        .padding()
        .background(Color(.systemGray6))
    }
    
    // MARK: - Sportsbook Section
    private var sportsbookSection: some View {
        HStack {
            // Sportsbook logo placeholder - implement later
            RoundedRectangle(cornerRadius: 8)
                .fill(Color.blue.opacity(0.1))
                .frame(width: 40, height: 30)
                .overlay(
                    Text(String(betSlip.sportsbook.displayName.prefix(2)))
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                )
            
            Text(betSlip.sportsbook.displayName)
                .font(.subheadline)
                .fontWeight(.medium)
            
            Spacer()
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .fill(Color(.systemGray4))
                .frame(height: 1),
            alignment: .bottom
        )
    }
    
    // MARK: - Bet Type Selector
    private var betTypeSelector: some View {
        HStack(spacing: 0) {
            ForEach([BetType.moneyline, BetType.spread, BetType.total], id: \.self) { betType in
                Button(action: {
                    selectedBetType = betType
                    selectedBet = nil
                    betAmount = ""
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
            ForEach(Array(betSlip.bettingLines.moneyline.keys.sorted()), id: \.self) { team in
                if let odds = betSlip.bettingLines.moneyline[team] {
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
            ForEach(Array(betSlip.bettingLines.spread.keys.sorted()), id: \.self) { spread in
                if let odds = betSlip.bettingLines.spread[spread] {
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
            ForEach(Array(betSlip.bettingLines.total.keys.sorted()), id: \.self) { total in
                if let odds = betSlip.bettingLines.total[total] {
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
    
    // MARK: - Prediction Section
    private func predictionSection(_ prediction: PredictionInfo) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.purple)
                Text("Prediction")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Spacer()
                Text(prediction.confidencePercentage)
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(.purple)
            }
            
            if let recommendedBet = prediction.recommendedBet {
                HStack {
                    Text("Recommended:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(recommendedBet)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(.purple)
                }
            }
            
            if let analysis = prediction.analysis {
                Text(analysis)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding()
        .background(Color.purple.opacity(0.05))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.purple.opacity(0.2), lineWidth: 1)
        )
        .padding(.horizontal)
        .padding(.bottom)
    }
    
    // MARK: - Helper Functions
    private func betTypeDisplayName(_ betType: BetType) -> String {
        switch betType {
        case .moneyline:
            return "Moneyline"
        case .spread:
            return "Spread"
        case .total:
            return "Total"
        }
    }
}

// MARK: - Bet Option Row
struct BetOptionRow: View {
    let selection: String
    let odds: Double
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(selection)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.primary)
                    
                    Text(formatOdds(odds))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Text(formatOdds(odds))
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(isSelected ? .white : .blue)
            }
            .padding()
            .background(isSelected ? Color.blue : Color(.systemGray6))
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

// MARK: - Preview
#Preview {
    ScrollView {
        VStack(spacing: 20) {
            // Create a sample BetSlip for preview
            BetSlipUI(betSlip: sampleBetSlip) { betType, selection, odds, amount in
                print("Tracking bet: \(selection) for $\(amount)")
            }
        }
        .padding()
    }
    .background(Color(.systemGroupedBackground))
}

// MARK: - Sample Data for Preview
private let sampleBetSlip = BetSlip(
    id: "preview",
    gameID: "preview",
    sportsbook: .draftkings,
    homeTeam: Team(
        id: "DUKE",
        name: "Duke Blue Devils",
        shortName: "DUKE",
        logoURL: "",
        record: TeamRecord(wins: 23, losses: 8),
        conference: "ACC",
        ranking: 9,
        colorHex: "#001A57"
    ),
    awayTeam: Team(
        id: "UNC",
        name: "North Carolina Tar Heels",
        shortName: "UNC",
        logoURL: "",
        record: TeamRecord(wins: 21, losses: 10),
        conference: "ACC",
        ranking: 15,
        colorHex: "#4B9CD3"
    ),
    gameTime: Date(),
    bettingLines: BettingLines(
        id: "preview",
        gameID: "preview",
        moneyline: ["DUKE": -150, "UNC": 130],
        spread: ["DUKE -3.5": -110, "UNC +3.5": -110],
        total: ["Over 145.5": -110, "Under 145.5": -110]
    ),
    predictionInfo: PredictionInfo(
        confidence: 85.0,
        recommendedBet: "UNC +3.5",
        analysis: "Strong defensive matchup favors the underdog"
    ),
    neutralSite: false
)
