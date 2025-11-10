import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
  Dimensions,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { colors } from '../theme/colors';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface ImagePickerModalProps {
  visible: boolean;
  onClose: () => void;
  onImageSelected: (imageUri: string) => void;
}

export const ImagePickerModal: React.FC<ImagePickerModalProps> = ({
  visible,
  onClose,
  onImageSelected,
}) => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const requestPermissions = async () => {
    const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
    const { status: libraryStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (cameraStatus !== 'granted' || libraryStatus !== 'granted') {
      Alert.alert(
        'Permission Required',
        'Please grant camera and photo library permissions to continue.'
      );
      return false;
    }
    return true;
  };

  const pickFromCamera = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        await processImage(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error picking from camera:', error);
      Alert.alert('Error', 'Failed to capture image');
    }
  };

  const pickFromLibrary = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        await processImage(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error picking from library:', error);
      Alert.alert('Error', 'Failed to select image');
    }
  };

  const processImage = async (uri: string) => {
    try {
      setProcessing(true);
      
      // Get image info
      const manipulateResult = await ImageManipulator.manipulateAsync(
        uri,
        [{ resize: { width: 1200 } }], // Resize to reasonable size
        { compress: 0.8, format: ImageManipulator.SaveFormat.JPEG }
      );

      setSelectedImage(manipulateResult.uri);
      setProcessing(false);
    } catch (error) {
      console.error('Error processing image:', error);
      setProcessing(false);
      Alert.alert('Error', 'Failed to process image');
    }
  };

  const handleSend = () => {
    if (selectedImage) {
      onImageSelected(selectedImage);
      handleClose();
    }
  };

  const handleClose = () => {
    setSelectedImage(null);
    setProcessing(false);
    onClose();
  };

  const renderImagePreview = () => {
    if (!selectedImage) return null;

    return (
      <View style={styles.previewContainer}>
        <View style={styles.previewHeader}>
          <Text style={styles.previewTitle}>Preview</Text>
          <TouchableOpacity onPress={() => setSelectedImage(null)} style={styles.clearButton}>
            <Ionicons name="close-circle" size={28} color={colors.error} />
          </TouchableOpacity>
        </View>
        
        <ScrollView 
          contentContainerStyle={styles.imageScrollContainer}
          showsVerticalScrollIndicator={false}
        >
          <Image
            source={{ uri: selectedImage }}
            style={styles.previewImage}
            resizeMode="contain"
          />
        </ScrollView>

        <View style={styles.previewActions}>
          <TouchableOpacity style={styles.editButton} onPress={() => setSelectedImage(null)}>
            <Ionicons name="create-outline" size={24} color={colors.primary} />
            <Text style={styles.editButtonText}>Choose Another</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.sendImageButton} onPress={handleSend}>
            <Ionicons name="send" size={20} color={colors.textLight} />
            <Text style={styles.sendImageButtonText}>Send Image</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const renderOptions = () => {
    return (
      <View style={styles.optionsContainer}>
        <Text style={styles.title}>Select Image Source</Text>
        
        <TouchableOpacity style={styles.optionButton} onPress={pickFromCamera}>
          <View style={styles.optionIconContainer}>
            <Ionicons name="camera" size={32} color={colors.primary} />
          </View>
          <View style={styles.optionContent}>
            <Text style={styles.optionTitle}>Camera</Text>
            <Text style={styles.optionSubtitle}>Take a new photo</Text>
          </View>
          <Ionicons name="chevron-forward" size={24} color={colors.textMuted} />
        </TouchableOpacity>

        <TouchableOpacity style={styles.optionButton} onPress={pickFromLibrary}>
          <View style={styles.optionIconContainer}>
            <Ionicons name="images" size={32} color={colors.primary} />
          </View>
          <View style={styles.optionContent}>
            <Text style={styles.optionTitle}>Photo Library</Text>
            <Text style={styles.optionSubtitle}>Choose from your photos</Text>
          </View>
          <Ionicons name="chevron-forward" size={24} color={colors.textMuted} />
        </TouchableOpacity>

        <TouchableOpacity style={styles.cancelButton} onPress={handleClose}>
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
    >
      <View style={styles.modalBackdrop}>
        <View style={styles.modalContent}>
          {processing ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={colors.primary} />
              <Text style={styles.loadingText}>Processing image...</Text>
            </View>
          ) : selectedImage ? (
            renderImagePreview()
          ) : (
            renderOptions()
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.textLight,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: SCREEN_HEIGHT * 0.9,
  },
  optionsContainer: {
    padding: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 24,
    textAlign: 'center',
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  optionIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.textLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  optionContent: {
    flex: 1,
  },
  optionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  optionSubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  cancelButton: {
    marginTop: 12,
    padding: 16,
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
  },
  loadingContainer: {
    padding: 48,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: colors.textSecondary,
  },
  previewContainer: {
    height: SCREEN_HEIGHT * 0.85,
  },
  previewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  previewTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.text,
  },
  clearButton: {
    padding: 4,
  },
  imageScrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  previewImage: {
    width: SCREEN_WIDTH - 32,
    height: SCREEN_HEIGHT * 0.6,
    borderRadius: 12,
  },
  previewActions: {
    flexDirection: 'row',
    padding: 20,
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  editButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.primary,
    gap: 8,
  },
  editButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.primary,
  },
  sendImageButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  sendImageButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textLight,
  },
});
