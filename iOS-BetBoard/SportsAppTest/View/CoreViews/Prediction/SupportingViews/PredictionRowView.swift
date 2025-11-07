import SwiftUI

struct PredictionRowView: View {
    let prediction: PredictionGame
    @EnvironmentObject var predictionsViewModel: PredictionsViewModel
    
    var body: some View {
        VStack(spacing: 12) {
            // Game Info Header
            HStack {
                // Away Team
                HStack(spacing: 6) {
                    if let awayRanking = prediction.awayTeam.ranking {
                        Text("#\(awayRanking)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                    }
                    
                    Text(prediction.awayTeam.displayName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Text("@")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                // Home Team
                HStack(spacing: 6) {
                    if let homeRanking = prediction.homeTeam.ranking {
                        Text("#\(homeRanking)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                    }
                    
                    Text(prediction.homeTeam.displayName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                // Game Time
                Text(prediction.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // Best Bet Info
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(getBetTypeText())
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text(getBestSelection())
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("(\(prediction.bestBet.sportsbook.displayName))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text(formatOdds(prediction.bestBet.odds))
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.blue)
                }
            }
            
            // Confidence Bar
            HStack {
                Text("Confidence")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                HStack(spacing: 8) {
                    // Confidence Bar
                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color(.systemGray5))
                                .frame(height: 6)
                                .cornerRadius(3)
                            
                            Rectangle()
                                .fill(confidenceColor(for: getTypeSpecificConfidence()))
                                .frame(width: geometry.size.width * CGFloat(getTypeSpecificConfidence() / 100.0), height: 6)
                                .cornerRadius(3)
                        }
                    }
                    .frame(width: 80, height: 6)
                    
                    Text("\(Int(getTypeSpecificConfidence()))%")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(confidenceColor(for: getTypeSpecificConfidence()))
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    // Get the appropriate bet type text based on the selected bet type
    private func getBetTypeText() -> String {
        switch predictionsViewModel.selectedBetType {
        case .moneyline:
            return "Moneyline Pick"
        case .spread:
            return "Spread Pick"
        case .total:
            return "Total Pick"
        }
    }
    
    // Get the appropriate selection based on the selected bet type
    // Get the appropriate selection based on the selected bet type
       private func getBestSelection() -> String {
           switch predictionsViewModel.selectedBetType {
           case .moneyline:
               if let bet = prediction.betSlip.predictionInfo?.moneylineBet {
                   return TeamNameFormatter.formatTeamName(bet)
               }
               return "N/A"
               
           case .spread:
               if let bet = prediction.betSlip.predictionInfo?.spreadBet {
                   // Format team name in spread bet (e.g., "CHARLESTON-SOUTHERN -2.0")
                   let components = bet.components(separatedBy: " ")
                   if components.count >= 2 {
                       let teamName = components[0]

                       return "\(TeamNameFormatter.formatTeamName(teamName))"
                   }
                   return bet
               }
               return "N/A"
               
           case .total:
               return prediction.betSlip.predictionInfo?.totalBet ?? "N/A"
           }
       }
    
    // Get the confidence specific to the selected bet type
    private func getTypeSpecificConfidence() -> Double {
        switch predictionsViewModel.selectedBetType {
        case .moneyline:
            return prediction.betSlip.predictionInfo?.moneylineConfidence ?? 0
        case .spread:
            return prediction.betSlip.predictionInfo?.spreadConfidence ?? 0
        case .total:
            return prediction.betSlip.predictionInfo?.totalConfidence ?? 0
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func confidenceColor(for confidence: Double) -> Color {
        if confidence >= 55 {
            return .green
        } else if confidence >= 50 {
            return .orange
        } else if confidence >= 40 {
            return .yellow
        } else {
            return .red
        }
    }
}
