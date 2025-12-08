//
//  HowItWorksView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct HowItWorksView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                VStack(alignment: .leading, spacing: 12) {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 50))
                        .foregroundColor(.purple)
                    
                    Text("How Our Predictions Work")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Understanding the technology behind BetBoard's predictions")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .padding(.bottom)
                
                // How It Works Steps
                VStack(alignment: .leading, spacing: 20) {
                    ForEach([
                        ("1", "Data Collection", "We gather comprehensive data including team statistics, historical matchups, and current season trends."),
                        ("2", "Algorithm Analysis", "Our machine learning algorithms analyze multiple factors including offensive/defensive efficiency, pace of play, and situational performance."),
                        ("3", "Predictions", "For every NCAA D1 Men's Basketball game, we provide win probability for each team, the predicted margin and the predicted total points."),
                        ("4", "Line Comparison", "We compare our predictions against current sportsbook lines to identify potential value bets.")
                    ], id: \.0) { step, title, description in
                        HStack(alignment: .top, spacing: 16) {
                            Text(step)
                                .font(.title)
                                .fontWeight(.bold)
                                .foregroundColor(.purple)
                                .frame(width: 30)
                            
                            VStack(alignment: .leading, spacing: 8) {
                                Text(title)
                                    .font(.headline)
                                    .fontWeight(.semibold)
                                
                                Text(description)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                
                Divider()
                
                // Factors Considered
                VStack(alignment: .leading, spacing: 16) {
                    Text("Key Factors We Analyze")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 2), spacing: 12) {
                        ForEach([
                            "Offensive Efficiency",
                            "Defensive Efficiency",
                            "Tempo (Pace)",
                            "W/L Record",
                            "Power Rating Difference",
                            "Recent Performance",
                            "Head-to-Head History",
                            "Home/Away Splits",
                            "Conference Strength",
                            "Neutral Site Games"
                        ], id: \.self) { factor in
                            Text("• \(factor)")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                
                Divider()
                
                // Disclaimer
                VStack(alignment: .leading, spacing: 12) {
                    Text("Remember")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Our predictions are based on statistical analysis and machine learning, but sports can be unpredictable. Use our predictions a tool in your decision-making process, not as guaranteed outcomes.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
        }
        .navigationTitle("How It Works")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationView {
        HowItWorksView()
    }
}
