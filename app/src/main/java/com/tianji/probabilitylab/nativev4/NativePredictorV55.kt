package com.tianji.probabilitylab.nativev4

import com.tianji.probabilitylab.nativev4.ai.NativeEnsemblePredictor
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import kotlin.math.roundToInt

const val NATIVE_ALGORITHM_VERSION_V55 = "native-ensemble-5.0"

/**
 * Versioned entry point for the v5.5 report pipeline.
 *
 * The statistical ensemble remains backward-compatible, while report metadata and data adequacy
 * now use each lottery's own verified-history target instead of a global 3,000-draw denominator.
 */
fun NativeEnsemblePredictor.predict(
    historyInput: List<Draw>,
    historyTarget: Int,
    payoutMultiplier: Double = 9.8,
): ForecastReport {
    val report = predict(historyInput, payoutMultiplier)
    val minimumTarget = 180
    val adequacy = (
        historyInput.size / historyTarget.coerceAtLeast(minimumTarget).toDouble() * 100.0
        ).roundToInt().coerceIn(10, 100)
    return report.copy(
        algorithmVersion = NATIVE_ALGORITHM_VERSION_V55,
        dataAdequacy = adequacy,
    )
}
