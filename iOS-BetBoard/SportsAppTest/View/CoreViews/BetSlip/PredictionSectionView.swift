//
//  PredictionSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


import SwiftUI

struct PredictionSectionView: View {
    let prediction: PredictionInfo
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.purple)
                Text("Our Prediction")
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
}
