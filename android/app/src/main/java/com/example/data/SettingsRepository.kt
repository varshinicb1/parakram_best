package com.example.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStorePref: DataStore<Preferences> by preferencesDataStore(name = "tinkr_settings")

class SettingsRepository(private val context: Context) {

    companion object {
        val KEY_LANGUAGE = stringPreferencesKey("language")
        val KEY_PERSONA = stringPreferencesKey("persona")
        val KEY_ACTIVE_BOARD = stringPreferencesKey("active_board")
        val KEY_SIMULATOR_MODE = booleanPreferencesKey("simulator_mode")
        val KEY_LOCAL_MODEL_DOWNLOADED = booleanPreferencesKey("local_model_downloaded")
        val KEY_ONBOARDING_COMPLETED = booleanPreferencesKey("onboarding_completed")
        val KEY_DARK_THEME = booleanPreferencesKey("dark_theme")
    }

    val languageFlow: Flow<String> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_LANGUAGE] ?: "en" }

    val personaFlow: Flow<String> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_PERSONA] ?: "engineer" }

    val activeBoardFlow: Flow<String> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_ACTIVE_BOARD] ?: "" }

    val isSimulatorModeFlow: Flow<Boolean> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_SIMULATOR_MODE] ?: true }

    val isLocalModelDownloadedFlow: Flow<Boolean> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_LOCAL_MODEL_DOWNLOADED] ?: false }

    val isOnboardingCompletedFlow: Flow<Boolean> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_ONBOARDING_COMPLETED] ?: false }

    val isDarkThemeFlow: Flow<Boolean> = context.dataStorePref.data
        .map { preferences -> preferences[KEY_DARK_THEME] ?: true }

    suspend fun setLanguage(languageCode: String) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_LANGUAGE] = languageCode
        }
    }

    suspend fun setPersona(personaId: String) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_PERSONA] = personaId
        }
    }

    suspend fun setActiveBoardAddress(address: String) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_ACTIVE_BOARD] = address
        }
    }

    suspend fun setSimulatorMode(enabled: Boolean) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_SIMULATOR_MODE] = enabled
        }
    }

    suspend fun setLocalModelDownloaded(downloaded: Boolean) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_LOCAL_MODEL_DOWNLOADED] = downloaded
        }
    }

    suspend fun setOnboardingCompleted(completed: Boolean) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_ONBOARDING_COMPLETED] = completed
        }
    }

    suspend fun setDarkTheme(enabled: Boolean) {
        context.dataStorePref.edit { preferences ->
            preferences[KEY_DARK_THEME] = enabled
        }
    }
}
