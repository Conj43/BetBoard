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
            if let photoURL = authService.currentUser?.photoURL {
                AsyncImage(url: photoURL) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    ProgressView()
                }
                .frame(width: 50, height: 50)
                .clipShape(Circle())
            } else {
                //Fallback if no photo available
                Circle()
                    .fill(Color.blue.opacity(0.2))
                    .frame(width: 50, height: 50)
                    .overlay(
                        Text(userInitials)
                            .font(.headline)
                            .fontWeight(.medium)
                            .foregroundColor(.blue)
                    )
            }
            
            // PREVIOUS IMAGE PLACEHOLDER
            /*
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
             */
            
            VStack(alignment: .leading, spacing: 4) {
                //PREVIOUS NAME STUFF
                /*
                Text(viewModel.settings?.userID.suffix(8).uppercased() ?? "User")
                    .font(.headline)
                    .fontWeight(.medium)
                
                Text("Anonymous User")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                 */
                Text(authService.currentUser?.displayName ?? "User")
                    .font(.headline)
                    .fontWeight(.medium)
                
                Text(authService.currentUser?.email ?? "No email associated")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
        .padding(.vertical, 8)
    }
    
    // PREVIOUS userInitials FUNCTION
    /*
    private var userInitials: String {
        guard let userID = authService.currentUser?.uid else { return "U" }
        return String(userID.prefix(2)).uppercased()
    }
     */
    private var userInitials: String {
        let name = authService.currentUser?.displayName ?? ""
        if let first = name.first {
            return String(first).uppercased()
        } else if let uid = authService.currentUser?.uid {
            return String(uid.prefix(2)).uppercased()
        }
        return "U"
    }
}
