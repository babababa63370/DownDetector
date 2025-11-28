import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';

export default function App() {
  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Mon Application Mobile</Text>
      </View>
      
      <View style={styles.content}>
        <Text style={styles.subtitle}>Bienvenue! 👋</Text>
        <Text style={styles.text}>
          Ceci est votre première application mobile créée avec React Native et Expo.
        </Text>
        
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Fonctionnalités</Text>
          <Text style={styles.bullet}>✓ Interface réactive</Text>
          <Text style={styles.bullet}>✓ Compatible mobile et web</Text>
          <Text style={styles.bullet}>✓ Facile à modifier</Text>
        </View>
        
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Commencez à développer</Text>
          <Text style={styles.text}>
            Modifiez ce fichier App.js pour personnaliser votre application!
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#6c63ff',
    paddingTop: 40,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  content: {
    padding: 20,
  },
  subtitle: {
    fontSize: 24,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  text: {
    fontSize: 16,
    color: '#666',
    lineHeight: 24,
    marginBottom: 16,
  },
  section: {
    marginTop: 20,
    marginBottom: 20,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  bullet: {
    fontSize: 16,
    color: '#555',
    marginBottom: 8,
  },
});
