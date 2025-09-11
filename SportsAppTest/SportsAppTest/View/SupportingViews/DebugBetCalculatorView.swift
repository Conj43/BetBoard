//
//  DebugBetCalculatorView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/27/25.
//


//
//  DebugBetCalculatorView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/27/25.
//

import SwiftUI

struct DebugBetCalculatorView: View {
    @State private var homeTeam = "DUKE"
    @State private var awayTeam = "UNC"
    @State private var homeScore = "75"
    @State private var awayScore = "68"
    @State private var betSelection = "UNC ML"
    @State private var betType: BetType = .moneyline
    @State private var calculatedResult: BetResult = .pending
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                Text("Bet Calculator Debug")
                    .font(.title)
                    .fontWeight(.bold)
                
                // Game Info Section
                VStack(alignment: .leading, spacing: 12) {
                    Text("Game Information")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    HStack(spacing: 20) {
                        VStack {
                            Text("Away Team")
                                .font(.caption)
                            TextField("Away", text: $awayTeam)
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                            TextField("Score", text: $awayScore)
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                                .keyboardType(.numberPad)
                        }
                        
                        Text("@")
                            .font(.title2)
                        
                        VStack {
                            Text("Home Team")
                                .font(.caption)
                            TextField("Home", text: $homeTeam)
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                            TextField("Score", text: $homeScore)
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                                .keyboardType(.numberPad)
                        }
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)
                
                // Bet Info Section
                VStack(alignment: .leading, spacing: 12) {
                    Text("Bet Information")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Picker("Bet Type", selection: $betType) {
                        Text("Moneyline").tag(BetType.moneyline)
                        Text("Spread").tag(BetType.spread)
                        Text("Total").tag(BetType.total)
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    
                    TextField("Bet Selection (e.g., UNC ML, DUKE -3.5, Over 145.5)", text: $betSelection)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)
                
                // Calculate Button
                Button("Calculate Result") {
                    calculateBetResult()
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .cornerRadius(12)
                
                // Result Section
                VStack(alignment: .leading, spacing: 12) {
                    Text("Calculated Result")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    HStack {
                        Text("Bet Result:")
                            .font(.subheadline)
                        
                        Spacer()
                        
                        Text(calculatedResult.rawValue.capitalized)
                            .font(.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(calculatedResult == .won ? .green : 
                                           calculatedResult == .lost ? .red : 
                                           calculatedResult == .push ? .orange : .gray)
                    }
                    
                    // Debug info
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Debug Info:")
                            .font(.caption)
                            .fontWeight(.semibold)
                        
                        Text("Game: \(awayTeam) \(awayScore) @ \(homeTeam) \(homeScore)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Text("Bet: \(betSelection) (\(betType.rawValue))")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        if betType == .total {
                            let gameTotal = (Int(homeScore) ?? 0) + (Int(awayScore) ?? 0)
                            Text("Game Total: \(gameTotal)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)
                
                Spacer()
            }
            .padding()
            .navigationTitle("Debug Calculator")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private func calculateBetResult() {
        guard let homeScoreInt = Int(homeScore),
              let awayScoreInt = Int(awayScore) else {
            calculatedResult = .lost
            return
        }
        
        calculatedResult = calculateBetResultLogic(
            betType: betType,
            selection: betSelection,
            homeScore: homeScoreInt,
            awayScore: awayScoreInt,
            homeTeam: homeTeam,
            awayTeam: awayTeam
        )
        
        // Print debug info
        print("🔍 Debug Calculation:")
        print("📊 Game: \(awayTeam) \(awayScoreInt) @ \(homeTeam) \(homeScoreInt)")
        print("🎯 Bet: \(betSelection) (\(betType.rawValue))")
        print("✅ Result: \(calculatedResult.rawValue)")
    }
    
    private func calculateBetResultLogic(betType: BetType, selection: String, homeScore: Int, awayScore: Int, homeTeam: String, awayTeam: String) -> BetResult {
        switch betType {
        case .moneyline:
            let teamFromSelection = selection.replacingOccurrences(of: " ML", with: "").trimmingCharacters(in: .whitespaces)
            
            let winner: String
            if homeScore > awayScore {
                winner = homeTeam
            } else if awayScore > homeScore {
                winner = awayTeam
            } else {
                return .push
            }
            
            return teamFromSelection.uppercased() == winner.uppercased() ? .won : .lost
            
        case .spread:
            let components = selection.components(separatedBy: " ")
            guard components.count >= 2 else { return .lost }
            
            let teamFromSelection = components[0].trimmingCharacters(in: .whitespaces)
            let spreadString = components[1]
            
            guard let spread = Double(spreadString) else { return .lost }
            
            let isHomeBet = teamFromSelection.uppercased() == homeTeam.uppercased()
            let finalScore: Double
            
            if isHomeBet {
                finalScore = Double(homeScore) + spread
                return finalScore > Double(awayScore) ? .won : .lost
            } else {
                finalScore = Double(awayScore) + spread
                return finalScore > Double(homeScore) ? .won : .lost
            }
            
        case .total:
            let components = selection.components(separatedBy: " ")
            guard components.count >= 2,
                  let betTotal = Double(components[1]) else { return .lost }
            
            let gameTotal = Double(homeScore + awayScore)
            let isOver = selection.uppercased().contains("OVER")
            
            if gameTotal == betTotal {
                return .push
            } else if isOver {
                return gameTotal > betTotal ? .won : .lost
            } else {
                return gameTotal < betTotal ? .won : .lost
            }
        }
    }
}

#Preview {
    DebugBetCalculatorView()
}