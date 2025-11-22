//
//  PredictionDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI


struct PendingBet: Identifiable {
    let id = UUID()
    let betType: BetType
    let selection: String
    let odds: Double
}

struct PredictionDetailView: View {
    let prediction: PredictionGame
    @ObservedObject var viewModel: PredictionsViewModel
    
    @State private var selectedSportsbook: Sportsbook
    @State private var selectedBetType: BetType = .spread
    @State private var showingSportsbookPicker = false
    @State private var betAmount: String = ""
    @State private var isTrackingBet = false
    @State private var showTrackConfirmation = false
    @State private var trackedBetDetails: String = ""
    
    // single source of truth for tracking
    @State private var pendingBet: PendingBet?
    
    // Get game result if available
    private var gameResult: GameResult? {
        viewModel.gameResults[prediction.betSlip.gameID]
    }
    
    init(prediction: PredictionGame, viewModel: PredictionsViewModel) {
        self.prediction = prediction
        self.viewModel = viewModel
        _selectedSportsbook = State(initialValue: prediction.betSlip.sportsbook)
    }
    
    // Get current betting lines for selected sportsbook
    private var currentLines: BettingLines? {
        switch selectedSportsbook {
        case .draftkings:
            return prediction.betSlip.allBettingLines?.draftkings
        case .fanduel:
            return prediction.betSlip.allBettingLines?.fanduel
        case .betmgm:
            return prediction.betSlip.allBettingLines?.betmgm
        case .caesars:
            return prediction.betSlip.allBettingLines?.caesars
        case .pointsbet:
            return prediction.betSlip.allBettingLines?.pointsbet
        case .barstool:
            return prediction.betSlip.allBettingLines?.barstool
        case .betonlineag:
            return prediction.betSlip.allBettingLines?.betonlineag
        case .betrivers:
            return prediction.betSlip.allBettingLines?.betrivers
        case .bovada:
            return prediction.betSlip.allBettingLines?.bovada
        case .lowvig:
            return prediction.betSlip.allBettingLines?.lowvig
        }
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                teamMatchupCard
                
                sportsbookSelector
                betTypeTabs
                linesDisplay
                if prediction.betSlip.predictionInfo != nil {
                    ourPredictionsCard
                }
            }
            .padding()
        }
        .navigationTitle("Prediction Details")
        .navigationBarTitleDisplayMode(.inline)
        .background(Color(.systemGroupedBackground))
        .preferredColorScheme(viewModel.colorScheme)
        .sheet(item: $pendingBet) { pending in
            QuickTrackBetSheet(
                betType: pending.betType,
                selection: pending.selection,
                odds: pending.odds,
                sportsbook: selectedSportsbook,
                betAmount: $betAmount
            ) { type, selection, odds, amount in
                trackBetFromDetail(
                    betType: type,
                    selection: selection,
                    odds: odds,
                    amount: amount
                )
            }
            .presentationDetents([.fraction(0.35), .medium])
            .presentationDragIndicator(.visible)
        }
        .alert("Bet Tracked!", isPresented: $showTrackConfirmation) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(trackedBetDetails)
        }
        .disabled(isTrackingBet)
    }
    
    // MARK: - Team Matchup Card
    private var teamMatchupCard: some View {
        VStack(spacing: 16) {
            HStack {
                Text(formattedGameTime)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Show final score badge if game is complete
                if let result = gameResult {
                    Text("Final: \(result.finalScore)")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.blue)
                        .cornerRadius(8)
                }
            }
            
            HStack(spacing: 20) {
                VStack(spacing: 8) {
                    TeamLogoView(team: prediction.awayTeam, size: 60)
                    
                    HStack(spacing: 4) {
                        Text(prediction.awayTeam.shortName)
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        if let rank = prediction.betSlip.awayRanking {
                            Text("#\(rank)")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.black)
                                .cornerRadius(4)
                        }
                    }
                    
                    // Show actual score if game is complete
                    if let result = gameResult {
                        Text("\(result.awayScore)")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                            .foregroundColor(result.winner == "away" ? .green : .primary)
                    } else if prediction.betSlip.predictionInfo != nil {
                        VStack(spacing: 2) {
                            Text("Win Probability")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            Text("\(Int(getAwayWinProbability()))%")
                                .font(.title3)
                                .fontWeight(.bold)
                                .foregroundColor(.blue)
                        }
                        .padding(.vertical, 4)
                        .padding(.horizontal, 8)
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(6)
                    }
                }
                
                Text(gameResult != nil ? "@" : "VS")
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundColor(.secondary)
                
                VStack(spacing: 8) {
                    TeamLogoView(team: prediction.homeTeam, size: 60)
                    
                    HStack(spacing: 4) {
                        Text(prediction.homeTeam.shortName)
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        if let rank = prediction.betSlip.homeRanking {
                            Text("#\(rank)")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.black)
                                .cornerRadius(4)
                        }
                    }
                    
                    // Show actual score if game is complete
                    if let result = gameResult {
                        Text("\(result.homeScore)")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                            .foregroundColor(result.winner == "home" ? .green : .primary)
                    } else if prediction.betSlip.predictionInfo != nil {
                        VStack(spacing: 2) {
                            Text("Win Probability")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            Text("\(Int(getHomeWinProbability()))%")
                                .font(.title3)
                                .fontWeight(.bold)
                                .foregroundColor(.blue)
                        }
                        .padding(.vertical, 4)
                        .padding(.horizontal, 8)
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(6)
                    }
                }
            }
        }
        .padding()
        .background(cardBackground)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
    
    // MARK: - Sportsbook Selector
    private var sportsbookSelector: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Sportsbook")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.primary)
                .padding(.horizontal, 4)
            
            Button(action: {
                showingSportsbookPicker.toggle()
            }) {
                HStack {
                    Image("sb_\(selectedSportsbook.rawValue.lowercased())")
                        .resizable()
                        .frame(width: 24, height: 24)
                        .cornerRadius(4)
                    
                    Text(selectedSportsbook.displayName)
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    Spacer()
                    
                    Image(systemName: showingSportsbookPicker ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding()
                .background(cardBackground)
                .cornerRadius(10)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                )
            }
            
            if showingSportsbookPicker {
                VStack(spacing: 0) {
                    ForEach(availableSportsbooks(), id: \.self) { sportsbook in
                        Button(action: {
                            selectedSportsbook = sportsbook
                            showingSportsbookPicker = false
                        }) {
                            HStack {
                                Image("sb_\(sportsbook.rawValue.lowercased())")
                                    .resizable()
                                    .frame(width: 24, height: 24)
                                    .cornerRadius(4)
                                
                                Text(sportsbook.displayName)
                                    .foregroundColor(.primary)
                                
                                Spacer()
                                
                                if sportsbook == selectedSportsbook {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.blue)
                                }
                            }
                            .padding(.horizontal)
                            .padding(.vertical, 12)
                            .background(cardBackground)
                        }
                        
                        if sportsbook != availableSportsbooks().last {
                            Divider()
                        }
                    }
                }
                .background(cardBackground)
                .cornerRadius(10)
                .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                )
            }
        }
    }
    
    private var betTypeTabs: some View {
        HStack(spacing: 0) {
            ForEach([BetType.moneyline, .spread, .total], id: \.self) { betType in
                betTypeButton(for: betType)
            }
        }
        .cornerRadius(10)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
    
    private func betTypeButton(for betType: BetType) -> some View {
        Button(action: {
            selectedBetType = betType
        }) {
            Text(betType.displayName)
                .font(.subheadline)
                .fontWeight(selectedBetType == betType ? .semibold : .regular)
                .foregroundColor(selectedBetType == betType ? .white : .primary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(selectedBetType == betType ? Color.blue : cardBackground)
        }
    }
    
    // MARK: - Lines Display
    private var linesDisplay: some View {
        VStack(spacing: 12) {
            if let lines = currentLines {
                switch selectedBetType {
                case .moneyline:
                    moneylineView(lines: lines)
                case .spread:
                    spreadView(lines: lines)
                case .total:
                    totalView(lines: lines)
                }
            } else {
                Text("No lines available for \(selectedSportsbook.displayName)")
                    .foregroundColor(.secondary)
                    .padding()
            }
        }
        .padding()
        .background(cardBackground)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
    
    private func moneylineView(lines: BettingLines) -> some View {
        HStack(spacing: 12) {
            ForEach(Array(lines.moneyline.keys.sorted()), id: \.self) { team in
                if let odds = lines.moneyline[team] {
                    Button {
                        // Only allow tracking if game hasn't started
                        if gameResult == nil {
                            pendingBet = PendingBet(
                                betType: .moneyline,
                                selection: team,
                                odds: odds
                            )
                            betAmount = ""
                        }
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(team)
                                .font(.subheadline)
                                .fontWeight(.medium)
                                .lineLimit(1)
                            
                            Text(formatOdds(odds))
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundColor(.orange)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                    .disabled(gameResult != nil)
                    .opacity(gameResult != nil ? 0.6 : 1.0)
                }
            }
        }
    }
    
    private func spreadView(lines: BettingLines) -> some View {
        HStack(spacing: 12) {
            let spreadEntries = Array(lines.spread.keys.sorted())
            
            ForEach(spreadEntries, id: \.self) { key in
                if let odds = lines.spread[key] {
                    Button {
                        // Only allow tracking if game hasn't started
                        if gameResult == nil {
                            pendingBet = PendingBet(
                                betType: .spread,
                                selection: key,
                                odds: odds
                            )
                            betAmount = ""
                        }
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(extractTeamName(from: key))
                                .font(.subheadline)
                                .fontWeight(.medium)
                                .lineLimit(2)
                            
                            HStack(spacing: 4) {
                                Text(extractSpreadValue(from: key))
                                    .font(.title2)
                                    .fontWeight(.bold)
                                    .foregroundColor(.blue)
                                
                                Text(formatOdds(odds))
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(.orange)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                    .disabled(gameResult != nil)
                    .opacity(gameResult != nil ? 0.6 : 1.0)
                }
            }
        }
    }
    
    private func totalView(lines: BettingLines) -> some View {
        HStack(spacing: 12) {
            let totalEntries = Array(lines.total.keys.sorted())
            
            ForEach(totalEntries, id: \.self) { selection in
                if let odds = lines.total[selection] {
                    Button {
                        // Only allow tracking if game hasn't started
                        if gameResult == nil {
                            pendingBet = PendingBet(
                                betType: .total,
                                selection: selection,
                                odds: odds
                            )
                            betAmount = ""
                        }
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(selection)
                                .font(.subheadline)
                                .fontWeight(.medium)
                            
                            Text(formatOdds(odds))
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundColor(.orange)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                    .disabled(gameResult != nil)
                    .opacity(gameResult != nil ? 0.6 : 1.0)
                }
            }
        }
    }
    
    // MARK: - Our Predictions Card
    private var ourPredictionsCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.purple)
                Text("Our Predictions")
                    .font(.headline)
                    .fontWeight(.semibold)
                
                // Show overall model performance if game is complete
                if let result = gameResult, let predInfo = prediction.betSlip.predictionInfo {
                    Spacer()
                    modelPerformanceBadge(result: result, predInfo: predInfo)
                }
            }
            
            if let predInfo = prediction.betSlip.predictionInfo, let lines = currentLines {
                
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "dollarsign.circle.fill")
                            .foregroundColor(.green)
                            .font(.caption)
                        Text("Moneyline")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)
                        if let result = gameResult {
                            Spacer()
                            Text("Actual Winner: \(result.winner == "home" ? prediction.homeTeam.shortName : prediction.awayTeam.shortName)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    if !hasMoneylineOdds {
                        Text("No moneyline odds available for this game.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .padding(.vertical, 8)
                            .padding(.horizontal, 10)
                            .background(Color(.systemGray6).opacity(0.5))
                            .cornerRadius(8)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
                    } else {
                        VStack(spacing: 6) {
                            ForEach(Array(lines.moneyline.keys.sorted()), id: \.self) { team in
                                if let odds = lines.moneyline[team] {
                                    let isPick = isMoneylinePick(team: team)
                                    moneylineRowView(team: team, odds: odds, isOurPick: isPick)
                                }
                            }
                        }
                        
                        if let pickTeam = getMoneylinePickTeam() {
                            HStack {
                                Text("Our Pick: \(pickTeam)")
                                    .font(.caption)
                                    .fontWeight(.bold)
                                    .foregroundColor(.green)
                                
                                if let result = gameResult {
                                    let won = checkMoneylineWin(team: pickTeam, result: result)
                                    HStack(spacing: 2) {
                                        Image(systemName: won ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .font(.caption2)
                                        Text(won ? "CORRECT" : "INCORRECT")
                                            .font(.caption2)
                                            .fontWeight(.bold)
                                    }
                                    .foregroundColor(won ? .green : .red)
                                }
                            }
                        } else {
                            Text("No moneyline pick: both sides have negative edge vs the odds.")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding()
                .background(cardBackground)
                .cornerRadius(10)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                )
                
                Divider()
                
                if let spreadBet = predInfo.spreadBet {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: "arrow.left.arrow.right")
                                .foregroundColor(.blue)
                                .font(.caption)
                            Text("Spread")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)
                            
                            // Add prediction result badge if game is complete
                            if let result = gameResult {
                                Spacer()
                                let line = extractSpreadLineValue(from: spreadBet)
                                if let won = result.didBetWin(betType: .spread, selection: spreadBet, line: line) {
                                    HStack(spacing: 4) {
                                        Image(systemName: won ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .font(.caption)
                                        Text(won ? "Predicted Correctly" : "Predicted Wrong")
                                            .font(.caption)
                                            .fontWeight(.bold)
                                    }
                                    .foregroundColor(won ? .green : .red)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(won ? Color.green.opacity(0.2) : Color.red.opacity(0.2))
                                    .cornerRadius(6)
                                }
                            }
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(formattedSpreadSentence(from: spreadBet))
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.blue)
                            
                            // Show actual result details
                            if let result = gameResult {
                                let margin = abs(result.homeScore - result.awayScore)
                                let winner = result.winner == "home" ? prediction.homeTeam.shortName : prediction.awayTeam.shortName
                                Text("Actual Result: \(winner) won by \(margin) pts")
                                    .font(.caption)
                                    .fontWeight(.medium)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.top, 4)
                        
                        Text("Sportsbook Lines:")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                            .padding(.top, 8)
                        
                        VStack(spacing: 6) {
                            ForEach(Array(lines.spread.keys.sorted()), id: \.self) { selection in
                                if let odds = lines.spread[selection] {
                                    let isPick = isSpreadPick(selection: selection, ourPick: spreadBet)
                                    spreadRowView(
                                        selection: selection,
                                        odds: odds,
                                        isOurPick: isPick
                                    )
                                }
                            }
                        }
                    }
                    .padding()
                    .background(cardBackground)
                    .cornerRadius(10)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                }
                
                Divider()
                
                if let totalBet = predInfo.totalBet {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: "chart.line.uptrend.xyaxis")
                                .foregroundColor(.orange)
                                .font(.caption)
                            Text("Total")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)
                            
                            // Add prediction result badge if game is complete
                            if let result = gameResult {
                                Spacer()
                                let line = extractTotalLineValue(from: totalBet)
                                if let won = result.didBetWin(betType: .total, selection: totalBet, line: line) {
                                    HStack(spacing: 4) {
                                        Image(systemName: won ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .font(.caption)
                                        Text(won ? "Predicted Correctly" : "Predicted Wrong")
                                            .font(.caption)
                                            .fontWeight(.bold)
                                    }
                                    .foregroundColor(won ? .green : .red)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(won ? Color.green.opacity(0.2) : Color.red.opacity(0.2))
                                    .cornerRadius(6)
                                }
                            }
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Our Pick: \(totalBet)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.orange)
                            
                            // Show actual result details
                            if let result = gameResult {
                                let actualTotal = result.homeScore + result.awayScore
                                Text("Actual Total: \(actualTotal) points")
                                    .font(.caption)
                                    .fontWeight(.medium)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.top, 4)
                        
                        Text("Sportsbook Lines:")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                            .padding(.top, 8)
                        
                        VStack(spacing: 6) {
                            ForEach(Array(lines.total.keys.sorted()), id: \.self) { selection in
                                if let odds = lines.total[selection] {
                                    let isPick = isTotalPick(selection: selection, ourPick: totalBet)
                                    totalRowView(
                                        selection: selection,
                                        odds: odds,
                                        isOurPick: isPick
                                    )
                                }
                            }
                        }
                    }
                    .padding()
                    .background(cardBackground)
                    .cornerRadius(10)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                }
            }
        }
        .padding()
        .background(cardBackground)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
    
    // MARK: - Model Performance Badge
    private func modelPerformanceBadge(result: GameResult, predInfo: PredictionInfo) -> some View {
        // Use moneyline pick instead of win probability for the badge
        let pickTeam = getMoneylinePickTeam()
        
        // If no moneyline pick (no edge), fall back to win probability
        let correct: Bool
        if let pick = pickTeam {
            correct = checkMoneylineWin(team: pick, result: result)
        } else {
            // No moneyline pick, use win probability as fallback
            let homeWinProb = getHomeWinProbability()
            let awayWinProb = getAwayWinProbability()
            let predictedWinner = homeWinProb > awayWinProb ? "home" : "away"
            correct = predictedWinner == result.winner
        }
        
        return HStack(spacing: 4) {
            Image(systemName: correct ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.caption)
            Text(correct ? "Predicted Winner" : "Wrong Winner")
                .font(.caption)
                .fontWeight(.bold)
        }
        .foregroundColor(correct ? .green : .red)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(correct ? Color.green.opacity(0.2) : Color.red.opacity(0.2))
        .cornerRadius(6)
    }
    
    // MARK: - Card Background Helper
    private var cardBackground: Color {
        Color(.systemBackground)
    }
    
    // MARK: - Row View Helpers
    private func moneylineRowView(team: String, odds: Double, isOurPick: Bool) -> some View {
        HStack(spacing: 6) {
            Text(team)
                .font(.subheadline)
                .fontWeight(isOurPick ? .bold : .medium)
                .lineLimit(2)
            
            Spacer()
            
            HStack(spacing: 6) {
                Text(formatOdds(odds))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("\(Int(impliedProbability(from: odds)))%")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if isOurPick {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.caption)
                }
            }
        }
        .frame(minHeight: 52)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(isOurPick ? Color.green.opacity(0.15) : Color(.systemGray6).opacity(0.5))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
        )
    }
    
    private func spreadRowView(selection: String, odds: Double, isOurPick: Bool) -> some View {
        HStack(spacing: 6) {
            Text(selection)
                .font(.subheadline)
                .fontWeight(isOurPick ? .bold : .medium)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
            
            Spacer()
            
            HStack(spacing: 6) {
                Text(formatOdds(odds))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("\(Int(impliedProbability(from: odds)))%")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if isOurPick {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.blue)
                        .font(.caption)
                }
            }
        }
        .frame(minHeight: 52)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(isOurPick ? Color.blue.opacity(0.15) : Color(.systemGray6).opacity(0.5))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
        )
    }
    
    private func totalRowView(selection: String, odds: Double, isOurPick: Bool) -> some View {
        HStack(spacing: 6) {
            Text(selection)
                .font(.subheadline)
                .fontWeight(isOurPick ? .bold : .medium)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
            
            Spacer()
            
            HStack(spacing: 6) {
                Text(formatOdds(odds))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("\(Int(impliedProbability(from: odds)))%")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if isOurPick {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.orange)
                        .font(.caption)
                }
            }
        }
        .frame(minHeight: 52)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(isOurPick ? Color.orange.opacity(0.15) : Color(.systemGray6).opacity(0.5))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
        )
    }
    
    // MARK: - Result Checking Helpers
    private func checkMoneylineWin(team: String, result: GameResult) -> Bool {
        let teamUpper = team.uppercased()
        let awayUpper = prediction.awayTeam.name.uppercased()
        let homeUpper = prediction.homeTeam.name.uppercased()
        
        if teamUpper.contains(awayUpper) || awayUpper.contains(teamUpper) {
            return result.winner == "away"
        } else if teamUpper.contains(homeUpper) || homeUpper.contains(teamUpper) {
            return result.winner == "home"
        }
        return false
    }
    
    private func extractSpreadLineValue(from selection: String) -> Double? {
        let components = selection.components(separatedBy: " ")
        if let lastComponent = components.last,
           let lineValue = Double(lastComponent) {
            return lineValue
        }
        return nil
    }
    
    private func extractTotalLineValue(from selection: String) -> Double? {
        // Extract from "Over 150.5" or "Under 150.5"
        let components = selection.components(separatedBy: " ")
        for component in components {
            if let value = Double(component) {
                return value
            }
        }
        return nil
    }
    
    // MARK: - Helper Functions
    private func availableSportsbooks() -> [Sportsbook] {
        var sportsbooks: [Sportsbook] = []
        let allLines = prediction.betSlip.allBettingLines
        
        if allLines?.draftkings != nil { sportsbooks.append(.draftkings) }
        if allLines?.fanduel != nil { sportsbooks.append(.fanduel) }
        if allLines?.betmgm != nil { sportsbooks.append(.betmgm) }
        if allLines?.caesars != nil { sportsbooks.append(.caesars) }
        if allLines?.pointsbet != nil { sportsbooks.append(.pointsbet) }
        if allLines?.barstool != nil { sportsbooks.append(.barstool) }
        if allLines?.betonlineag != nil { sportsbooks.append(.betonlineag) }
        if allLines?.betrivers != nil { sportsbooks.append(.betrivers) }
        if allLines?.bovada != nil { sportsbooks.append(.bovada) }
        if allLines?.lowvig != nil { sportsbooks.append(.lowvig) }
        
        return sportsbooks
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE, MMM d 'at' h:mm a"
        return formatter.string(from: prediction.gameTime)
    }
    
    private func impliedProbability(from odds: Double) -> Double {
        if odds > 0 {
            return (100 / (odds + 100)) * 100
        } else {
            return (abs(odds) / (abs(odds) + 100)) * 100
        }
    }
    
    private func extractTeamName(from spreadString: String) -> String {
        let components = spreadString.components(separatedBy: " ")
        let teamComponents = components.dropLast()
        return teamComponents.joined(separator: " ")
    }
    
    private func extractSpreadValue(from spreadString: String) -> String {
        let components = spreadString.components(separatedBy: " ")
        if let lastComponent = components.last {
            return lastComponent
        }
        return ""
    }
    
    private func getHomeWinProbability() -> Double {
        guard let predInfo = prediction.betSlip.predictionInfo else { return 50.0 }
        
        if let pWinHome = predInfo.pWinHome {
            return (pWinHome * 100.0).rounded()
        }
        
        return 50.0
    }
    
    private func getAwayWinProbability() -> Double {
        return 100.0 - getHomeWinProbability()
    }
    
    // MARK: - Moneyline helpers
    private func getMoneylinePickTeam() -> String? {
        guard prediction.betSlip.predictionInfo != nil,
              let _ = currentLines else {
            return nil
        }
        
        let homeModelProb = getHomeWinProbability()
        let awayModelProb = getAwayWinProbability()
        
        guard let homeOdds = getMoneylineOdds(for: prediction.homeTeam.name),
              let awayOdds = getMoneylineOdds(for: prediction.awayTeam.name) else {
            return nil
        }
        
        let homeImpliedProb = impliedProbability(from: homeOdds)
        let awayImpliedProb = impliedProbability(from: awayOdds)
        
        let homeEdge = homeModelProb - homeImpliedProb
        let awayEdge = awayModelProb - awayImpliedProb
        
        let bestEdge = max(homeEdge, awayEdge)
        guard bestEdge > 0 else {
            return nil
        }
        
        if homeEdge >= awayEdge {
            return prediction.homeTeam.name
        } else {
            return prediction.awayTeam.name
        }
    }
    
    private func isMoneylinePick(team: String) -> Bool {
        guard let pick = getMoneylinePickTeam() else { return false }
        
        let teamUpper = team.uppercased()
        let pickUpper = pick.uppercased()
        
        return teamUpper == pickUpper ||
        teamUpper.contains(pickUpper) ||
        pickUpper.contains(teamUpper)
    }
    
    private func isSpreadPick(selection: String, ourPick: String) -> Bool {
        // Only highlight if the exact spread values match
        // Our model's spread is different from sportsbook lines, so don't highlight
        let selectionValue = extractSpreadLineValue(from: selection)
        let ourPickValue = extractSpreadLineValue(from: ourPick)
        
        guard let selValue = selectionValue, let ourValue = ourPickValue else {
            return false
        }
        
        // Check if team names match AND spread values are close (within 0.5)
        let selectionTeam = extractTeamName(from: selection).uppercased()
        let ourPickTeam = extractTeamName(from: ourPick).uppercased()
        
        let teamMatches = selectionTeam.contains(ourPickTeam) || ourPickTeam.contains(selectionTeam)
        let spreadMatches = abs(selValue - ourValue) < 0.5
        
        return teamMatches && spreadMatches
    }
    
    private func isTotalPick(selection: String, ourPick: String) -> Bool {
        let selectionUpper = selection.uppercased()
        let ourPickUpper = ourPick.uppercased()
        
        let bothOver = selectionUpper.contains("OVER") && ourPickUpper.contains("OVER")
        let bothUnder = selectionUpper.contains("UNDER") && ourPickUpper.contains("UNDER")
        
        return bothOver || bothUnder
    }
    
    private func getMoneylineOdds(for teamName: String) -> Double? {
        guard let lines = currentLines else { return nil }
        
        for (key, odds) in lines.moneyline {
            if key.uppercased().contains(teamName.uppercased()) ||
                teamName.uppercased().contains(key.uppercased()) {
                return odds
            }
        }
        return nil
    }
    
    private var hasMoneylineOdds: Bool {
        guard let lines = currentLines else { return false }
        return lines.moneyline.count >= 2
    }
    
    private func formattedSpreadSentence(from spreadBet: String) -> String {
        let parts = spreadBet.split(separator: " ")
        guard let last = parts.last,
              let value = Double(last) else {
            return "Our projected spread: \(spreadBet)"
        }
        
        let teamName = parts.dropLast().joined(separator: " ")
        let absValue = abs(value)
        
        if value < 0 {
            // Team is favorite, we predict them to win by this amount
            return "Our Pick: \(teamName) to win by \(String(format: "%.1f", absValue)) points"
        } else {
            // Team is underdog with positive spread - this shouldn't happen in our model
            // But if it does, show it clearly
            return "Our Pick: \(teamName) +\(String(format: "%.1f", value))"
        }
    }
    
    private func trackBetFromDetail(
        betType: BetType,
        selection: String,
        odds: Double,
        amount: Double
    ) {
        trackedBetDetails = "\(selection) at \(formatOdds(odds))"
        isTrackingBet = true
        
        Task {
            await viewModel.trackSpecificBet(
                from: prediction,
                betType: betType,
                selection: selection,
                odds: odds,
                amount: amount
            )
            
            await MainActor.run {
                isTrackingBet = false
                showTrackConfirmation = true
            }
        }
    }
}

struct QuickTrackBetSheet: View {
    let betType: BetType
    let selection: String
    let odds: Double
    let sportsbook: Sportsbook
    @Binding var betAmount: String
    
    let onTrack: (BetType, String, Double, Double) -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack(spacing: 16) {
                TrackBetSectionView(
                    selection: selection,
                    odds: odds,
                    selectedBetType: betType,
                    selectedSportsbook: sportsbook,
                    betAmount: $betAmount,
                    onTrackBet: { type, sel, odds, amount in
                        onTrack(type, sel, odds, amount)
                        dismiss()
                    }
                )
            }
            .padding()
            .navigationTitle("Track Bet")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
