//
//  AuthService.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import FirebaseAuth
import FirebaseFirestore
import Combine

@MainActor
class AuthService: ObservableObject {
    @Published var currentUser: FirebaseAuth.User?
    @Published var isSignedIn = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private var authStateListener: AuthStateDidChangeListenerHandle?
    
    init() {
        setupAuthStateListener()
    }
    
    deinit {
        if let listener = authStateListener {
            Auth.auth().removeStateDidChangeListener(listener)
        }
    }
    
    private func setupAuthStateListener() {
        authStateListener = Auth.auth().addStateDidChangeListener { [weak self] auth, user in
            Task { @MainActor in
                self?.currentUser = user
                self?.isSignedIn = user != nil
            }
        }
    }
    
    func signInAnonymously() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let result = try await Auth.auth().signInAnonymously()
            currentUser = result.user
            isSignedIn = true
        } catch {
            errorMessage = "Failed to sign in: \(error.localizedDescription)"
        }
        
        isLoading = false
    }
    
    func signOut() {
        do {
            try Auth.auth().signOut()
            currentUser = nil
            isSignedIn = false
        } catch {
            errorMessage = "Failed to sign out: \(error.localizedDescription)"
        }
    }
    
    func createUserProfile() async {
        guard let user = currentUser else { return }
        
        let userData: [String: Any] = [
            "username": "User\(String(user.uid.suffix(6)))",
            "email": user.email ?? "",
            "notificationsEnabled": true,
            "darkModeEnabled": false,
            "preferredOddsFormat": "american",
            "createdAt": Timestamp(date: Date())
        ]
        
        do {
            try await Firestore.firestore()
                .collection("users")
                .document(user.uid)
                .setData(userData, merge: true)
        } catch {
            errorMessage = "Failed to create user profile: \(error.localizedDescription)"
        }
    }
}
