//
//  UserProfileSectionView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI

struct UserProfileSectionView: View {
    let authService: AuthService
    let viewModel: InfoViewModel
    
    var body: some View {
        HStack {
            // Profile Image Placeholder
            Circle()
                .fill(Color.blue.opacity(0.2))
                .frame(width: 50, height: 50)
                .overlay(
                    Text(userInitials)
                        .font(.headline)
                        .fontWeight(.medium)
                        .foregroundColor(.blue)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text(viewModel.settings?.userID.suffix(8).uppercased() ?? "User")
                    .font(.headline)
                    .fontWeight(.medium)
                
                Text("Anonymous User")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
        .padding(.vertical, 8)
    }
    
    private var userInitials: String {
        guard let userID = authService.currentUser?.uid else { return "U" }
        return String(userID.prefix(2)).uppercased()
    }
}
