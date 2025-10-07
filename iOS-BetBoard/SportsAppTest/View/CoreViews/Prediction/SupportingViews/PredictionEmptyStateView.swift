//
//  PredictionEmptyStateView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  PredictionEmptyStateView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct PredictionEmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.bar.xaxis")
                .font(.largeTitle)
                .foregroundColor(.secondary)
            
            Text("No predictions available")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Check back later for AI predictions")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding()
    }
}