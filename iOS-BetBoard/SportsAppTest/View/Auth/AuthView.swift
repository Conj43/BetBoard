//
//  AuthView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//


import SwiftUI

struct AuthView: View {
    @ObservedObject var authService: AuthService
    
    var body: some View {
        VStack(spacing: 30) {
            // App Logo/Title
            VStack(spacing: 16) {
                Image(systemName: "chart.bar.xaxis")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)
                
                Text("BetBoard")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Track your sports bets with AI predictions")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            Spacer()
            
            // Sign In Button
            VStack(spacing: 16) {
                if authService.isLoading {
                    ProgressView("Signing in...")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                } else {
                    Button(action: {
                        Task {
                            await authService.signInAnonymously()
                            await authService.createUserProfile()
                        }
                    }) {
                        HStack {
                            Image(systemName: "person.fill")
                            Text("Get Started")
                        }
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .cornerRadius(12)
                    }
                }
                
                // Error Message
                if let errorMessage = authService.errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                }
            }
            
            Spacer()
            
            // Disclaimer
            Text("Anonymous sign-in for testing. No personal information required.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }
}
