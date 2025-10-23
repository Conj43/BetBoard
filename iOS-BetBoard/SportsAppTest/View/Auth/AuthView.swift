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
                
                Text("Track your sports bets with our predictions")
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
                            //await authService.signInAnonymously()
                            //await authService.createUserProfile()
                            await authService.signInWithGoogle()
                        }
                    }) {
                        HStack {
                            Image("googleLogo")
                                .resizable()
                                .frame(width: 20, height: 20)
                            Text("Sign in with Google")
                        }
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.green)
                        .cornerRadius(12)
                    }
                    
                    //Anonymous Sign-In Button
                    Button(action: {
                        Task { await authService.signInAnonymously()}
                    }) {
                        HStack {
                            Image(systemName: "person.fill")
                            Text("Sign in anonymously")
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
            Text("Anonymous sign-in for testing. Or give the Google Sign-In a try.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }
    
}
