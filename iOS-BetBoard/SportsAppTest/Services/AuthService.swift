//
//  AuthService.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import FirebaseAuth
import FirebaseFirestore
import GoogleSignIn
import UIKit
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
    
    // GOOGLE SIGN-IN
    func signInWithGoogle() async {
        isLoading = true
        errorMessage = nil
        
        guard let presentingVC = UIApplication.shared.connectedScenes
            .compactMap({ ($0 as? UIWindowScene)?.keyWindow?.rootViewController})
            .first else {
            errorMessage = "Unable to access the root view controller."
            isLoading = false
            return
        }
        
        do {
            //Start Google sign-in flow
            let signInResult = try await GIDSignIn.sharedInstance.signIn(withPresenting: presentingVC)
            
            //Extract Tokens
            guard let idToken = signInResult.user.idToken?.tokenString else {
                throw NSError(domain: "AuthService", code: 0, userInfo: [NSLocalizedDescriptionKey: "Missing ID token."])
            }
            let accessToken = signInResult.user.accessToken.tokenString
            
            // Create firebase credential
            let credential = GoogleAuthProvider.credential(withIDToken: idToken, accessToken: accessToken)
            
            // Sign in with Firebase
            let result = try await Auth.auth().signIn(with: credential)
            currentUser = result.user
            isSignedIn = true
            
            //Create/update user profile in Firestore
            await createUserProfile()
        } catch {
            errorMessage = "Google Sign-In failed: \(error.localizedDescription)"
        }
        
        isLoading = false
    }
    
    // Anonymous Sign-In, good for testing
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
     
    // OLD SIGN OUT FUNCTION
    /*
    func signOut() {
        do {
            try Auth.auth().signOut()
            currentUser = nil
            isSignedIn = false
        } catch {
            errorMessage = "Failed to sign out: \(error.localizedDescription)"
        }
    }
     */
    
    func signOut() {
        do {
            try Auth.auth().signOut()
            GIDSignIn.sharedInstance.signOut()
            currentUser = nil
            isSignedIn = false
        } catch {
            errorMessage = "Failed to sign out: \(error.localizedDescription)"
        }
    }
    
    func createUserProfile() async {
        guard let user = currentUser else { return }
        
        let userData: [String: Any] = [
            "username": user.displayName ?? "User\(String(user.uid.suffix(6)))",
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
