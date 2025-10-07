//
//  SearchEmptyStateView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct SearchEmptyStateView: View {
    let onPopularSearchTap: (String) -> Void
    
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 50))
                .foregroundColor(.secondary)
            
            Text("Search for teams")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Start typing to find games and betting opportunities")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            // Popular searches hint
            VStack(alignment: .leading, spacing: 8) {
                Text("Popular searches:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                HStack {
                    ForEach(["Duke", "UNC", "Virginia"], id: \.self) { teamName in
                        Button(teamName) {
                            onPopularSearchTap(teamName)
                        }
                        .font(.caption)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.blue.opacity(0.1))
                        .foregroundColor(.blue)
                        .cornerRadius(16)
                    }
                }
            }
            .padding(.top)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

#Preview {
    SearchEmptyStateView { teamName in
        print("Selected: \(teamName)")
    }
}
