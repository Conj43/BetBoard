//
//  AppInfoDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct AppInfoDetailView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // App Icon
                VStack(spacing: 16) {
                    Image(systemName: "chart.bar.xaxis")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)
                    
                    Text("BetBoard")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    Text("Version 1.0.0")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.bottom)
                
                // App Description
                VStack(alignment: .leading, spacing: 12) {
                    Text("What is BetBoard?")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("BetBoard is a sports betting analytics app that helps you make informed decisions by comparing odds across different sportsbooks and providing AI-powered predictions for college basketball games.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Divider()
                
                // Key Features
                VStack(alignment: .leading, spacing: 12) {
                    Text("Key Features")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    ForEach([
                        ("chart.bar.xaxis", "Our Predictions", "Get predictions for upcoming games"),
                        ("magnifyingglass", "Game Search", "Find games by team names and matchups"),
                        ("chart.line.uptrend.xyaxis", "Performance Tracking", "Track your betting performance over time"),
                        ("brain.head.profile", "Smart Analysis", "Detailed breakdowns of key factors for each game")
                    ], id: \.1) { icon, title, description in
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: icon)
                                .font(.title3)
                                .foregroundColor(.blue)
                                .frame(width: 25)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text(title)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                
                                Text(description)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                
                Divider()
                
                // Disclaimer
                VStack(alignment: .leading, spacing: 12) {
                    Text("Important Disclaimer")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("BetBoard is for informational and educational purposes only. We do not facilitate betting or gambling. All predictions are based on algorithmic analysis and should not be considered guaranteed outcomes. Please bet responsibly.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationView {
        AppInfoDetailView()
    }
}
