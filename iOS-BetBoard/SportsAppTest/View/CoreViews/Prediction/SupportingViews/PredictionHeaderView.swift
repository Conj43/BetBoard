//
//  PredictionHeaderView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI

struct PredictionHeaderView: View {
    let predictionsCount: Int
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.purple)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Predictions")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Our highest confidence bets")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Today")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    
                    Text("\(predictionsCount) Games")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(12)
            .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        }
        .padding(.horizontal)
        .padding(.top, 8)
    }
}
