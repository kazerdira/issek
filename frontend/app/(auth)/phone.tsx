import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '../../src/store/authStore';
import { authAPI } from '../../src/services/api';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';

export default function PhoneAuthScreen() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const [otpCode, setOtpCode] = useState('');

  const handleRequestOTP = async () => {
    if (!phoneNumber) {
      Alert.alert('Error', 'Please enter your phone number');
      return;
    }

    setLoading(true);
    try {
      const response = await authAPI.requestOTP(phoneNumber);
      // In dev mode, show the OTP
      if (response.data.otp) {
        setOtpCode(response.data.otp);
        Alert.alert('OTP Sent', `Your OTP is: ${response.data.otp}`);
      }
      setStep('otp');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (!otp) {
      Alert.alert('Error', 'Please enter the OTP');
      return;
    }

    setLoading(true);
    try {
      const response = await authAPI.verifyOTP(phoneNumber, otp);
      await login(response.data.access_token, response.data.user);
      router.replace('/(tabs)/chats');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={24} color={colors.text} />
      </TouchableOpacity>

      <View style={styles.content}>
        <View style={styles.header}>
          <Ionicons name="phone-portrait" size={64} color={colors.primary} />
          <Text style={styles.title}>
            {step === 'phone' ? 'Enter Your Phone' : 'Verify OTP'}
          </Text>
          <Text style={styles.subtitle}>
            {step === 'phone'
              ? 'We will send you a verification code'
              : `Code sent to ${phoneNumber}`}
          </Text>
        </View>

        {step === 'phone' ? (
          <View style={styles.form}>
            <View style={styles.inputContainer}>
              <Ionicons name="call-outline" size={20} color={colors.textSecondary} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="+1234567890"
                value={phoneNumber}
                onChangeText={setPhoneNumber}
                keyboardType="phone-pad"
              />
            </View>

            <TouchableOpacity
              style={styles.button}
              onPress={handleRequestOTP}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.textLight} />
              ) : (
                <Text style={styles.buttonText}>Send Code</Text>
              )}
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.form}>
            <View style={styles.inputContainer}>
              <Ionicons name="key-outline" size={20} color={colors.textSecondary} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter 6-digit code"
                value={otp}
                onChangeText={setOtp}
                keyboardType="number-pad"
                maxLength={6}
              />
            </View>

            {otpCode && (
              <Text style={styles.devOtp}>Dev OTP: {otpCode}</Text>
            )}

            <TouchableOpacity
              style={styles.button}
              onPress={handleVerifyOTP}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.textLight} />
              ) : (
                <Text style={styles.buttonText}>Verify</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.resendButton}
              onPress={handleRequestOTP}
            >
              <Text style={styles.resendText}>Resend Code</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  backButton: {
    position: 'absolute',
    top: 48,
    left: 16,
    zIndex: 1,
    padding: 8,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 24,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  form: {
    marginBottom: 24,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    paddingVertical: 16,
    fontSize: 16,
    color: colors.text,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: colors.textLight,
    fontSize: 16,
    fontWeight: '600',
  },
  resendButton: {
    marginTop: 16,
    padding: 16,
    alignItems: 'center',
  },
  resendText: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  devOtp: {
    fontSize: 14,
    color: colors.success,
    textAlign: 'center',
    marginBottom: 8,
    fontWeight: '600',
  },
});
