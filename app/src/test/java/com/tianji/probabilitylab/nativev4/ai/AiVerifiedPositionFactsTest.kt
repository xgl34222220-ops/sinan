package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.ConfidenceInterval
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.SourceHealth
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiVerifiedPositionFactsTest {
    @Test
    fun australianFirstPlaceUsesExactCurrentApiSnapshotInNewestFirstOrder() {
        val firstValues = listOf(7, 4, 5, 2, 2, 3, 10, 8, 4, 10)
        val draws = firstValues.mapIndexed { index, first ->
            draw(period = "213481${(8 + index).toString().padStart(2, '0')}", first = first, fourth = 6)
        }
        val snapshot = snapshot(draws)
        val facts = AiVerifiedPositionEngine.calculate(snapshot, report(snapshot), position = 0)

        assertEquals("澳洲幸运10", facts.lotteryName)
        assertEquals(listOf(10, 4, 8, 10, 3, 2, 2, 5, 4, 7), facts.recent10NewestFirst.map { it.number })
        assertEquals(2, facts.count20[1])
        assertEquals(2, facts.count120[9])
        assertEquals("21348118", facts.targetPeriod)
        assertEquals("upstream_lottery_api_current_response", facts.toJson().getString("source"))
    }

    @Test
    fun switchingFromFourthToFirstKeepsUiConversationButExcludesFourthRankEvidence() {
        val generic = AiChatMessage(role = AiChatRole.USER, content = "继续用真实数据")
        val fourthUser = AiChatMessage(
            role = AiChatRole.USER,
            content = "分析第四名",
            positionScope = 3,
        )
        val fourthAnswer = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "第四名旧分析",
            positionScope = 3,
        )
        val messages = listOf(generic, fourthUser, fourthAnswer)

        val first = AiPositionScope.resolve("改成分析第一名", messages)
        val scoped = AiPositionScope.filterPrevious(messages, first)

        assertEquals(0, first)
        assertTrue(generic in scoped)
        assertFalse(fourthUser in scoped)
        assertFalse(fourthAnswer in scoped)
    }

    @Test
    fun naturalFollowUpContinuesLastRankButAllRankRequestClearsScope() {
        val fourth = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "第四名分析完成",
            positionScope = 3,
        )

        assertEquals(3, AiPositionScope.resolve("为什么这么判断", listOf(fourth)))
        assertNull(AiPositionScope.resolve("比较十个名次", listOf(fourth)))
    }

    @Test
    fun freshSameRankQuestionDaysLaterDoesNotCarryOldMiss() {
        val oldMessage = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "第一名旧预测",
            targetPeriod = "21348001",
            positionScope = 0,
        )
        val oldRecord = settledRecord(target = "21348001", position = 0, actual = 9)

        val continuity = AiConversationContinuity.resolve(
            question = "分析第一名",
            activePosition = 0,
            currentTargetPeriod = "21348118",
            latestApiPeriod = "21348117",
            messages = listOf(oldMessage),
            candidates = listOf(oldRecord),
        )

        assertEquals(AiContinuityMode.FRESH, continuity.mode)
        assertTrue(continuity.previousMessages.isEmpty())
        assertTrue(continuity.relevantFeedback.isBlank())
    }

    @Test
    fun adjacentMissIsCarriedOnlyWhenUserContinuesToNextPeriod() {
        val previousQuestion = AiChatMessage(
            role = AiChatRole.USER,
            content = "预测第一名",
            targetPeriod = "21348117",
            positionScope = 0,
        )
        val previousAnswer = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "第一名候选1、2、3、4、5、6",
            targetPeriod = "21348117",
            positionScope = 0,
        )
        val record = settledRecord(target = "21348117", position = 0, actual = 9)

        val continuity = AiConversationContinuity.resolve(
            question = "不中，再看看下一期第一名",
            activePosition = 0,
            currentTargetPeriod = "21348118",
            latestApiPeriod = "21348117",
            messages = listOf(previousQuestion, previousAnswer),
            candidates = listOf(record),
        )

        assertEquals(AiContinuityMode.EXPLICIT_REVIEW, continuity.mode)
        assertEquals(record, continuity.relevantRecord)
        assertTrue(continuity.relevantFeedback.contains("目标期21348117"))
        assertTrue(continuity.relevantFeedback.contains("实际号码9"))
        assertTrue(continuity.relevantFeedback.contains("未中"))
        assertEquals(2, continuity.previousMessages.size)
    }

    @Test
    fun explicitOldReviewUsesExactPeriodAndDoesNotPretendItWasLastDraw() {
        val record = settledRecord(target = "21347000", position = 0, actual = 8)
        val continuity = AiConversationContinuity.resolve(
            question = "复盘上次第一名为什么没中",
            activePosition = 0,
            currentTargetPeriod = "21348118",
            latestApiPeriod = "21348117",
            messages = emptyList(),
            candidates = listOf(record),
        )

        assertEquals(AiContinuityMode.EXPLICIT_REVIEW, continuity.mode)
        assertTrue(continuity.relevantFeedback.contains("目标期21347000"))
        assertTrue(continuity.relevantFeedback.contains("不得称作上一期"))
    }

    @Test
    fun exactRecentLookupAnswersOnlyFromCurrentApiFacts() {
        val draws = listOf(7, 4, 5, 2, 2, 3, 10, 8, 4, 10).mapIndexed { index, first ->
            draw(period = "213481${(8 + index).toString().padStart(2, '0')}", first = first, fourth = 6)
        }
        val snapshot = snapshot(draws)
        val facts = AiVerifiedPositionEngine.calculate(snapshot, report(snapshot), position = 0)
        val composed = AiVerifiedAnswerComposer.compose(
            modelText = "近10期第一名号码：7→3→5→1→5→3→4→6→2→7",
            facts = facts,
            intent = AiChatIntent.LOTTERY_ANALYSIS,
            question = "第一名最近十期号码是什么",
        )

        assertTrue(composed.contains("澳洲幸运10第1名最近10期"))
        assertTrue(composed.contains("21348117期=10"))
        assertFalse(composed.contains("7→3→5→1"))
        assertTrue(composed.contains("上游开奖 API"))
    }

    @Test
    fun generalAnalysisKeepsNaturalInterpretationButDoesNotForceUnusedStatistics() {
        val draws = listOf(7, 4, 5, 2, 2, 3, 10, 8, 4, 10).mapIndexed { index, first ->
            draw(period = "213481${(8 + index).toString().padStart(2, '0')}", first = first, fourth = 6)
        }
        val snapshot = snapshot(draws)
        val facts = AiVerifiedPositionEngine.calculate(snapshot, report(snapshot), position = 0)
        val composed = AiVerifiedAnswerComposer.compose(
            modelText = "近120期3号出现18次。\n整体波动较大，信号并不稳定。",
            facts = facts,
            intent = AiChatIntent.LOTTERY_ANALYSIS,
            question = "分析第一名",
        )

        assertFalse(composed.contains("3号出现18次"))
        assertTrue(composed.contains("整体波动较大"))
        assertTrue(composed.contains("数据源：澳洲幸运10上游开奖 API"))
        assertFalse(composed.contains("最近10期（新→旧）"))
    }

    @Test
    fun routerKeepsNormalChatFreeAndUnderstandsMissThenNextPeriod() {
        assertEquals(AiChatIntent.FREE_CHAT, AiChatIntentRouter.resolve("一加一等于几"))
        assertEquals(AiChatIntent.LOTTERY_ANALYSIS, AiChatIntentRouter.resolve("不中"))
        assertEquals(
            AiChatIntent.LOTTERY_PREDICTION,
            AiChatIntentRouter.resolve("不中，再看看下一期第一名"),
        )
    }

    private fun settledRecord(target: String, position: Int, actual: Int): AiChatCandidateRecord =
        AiChatCandidateRecord(
            messageId = "message-$target",
            targetPeriod = target,
            prediction = AiChatPrediction(
                position = position,
                top6 = listOf(1, 2, 3, 4, 5, 6),
                top7 = listOf(1, 2, 3, 4, 5, 6, 7),
                probabilities = List(10) { 0.1 },
            ),
            actualNumber = actual,
            resolvedPeriod = target,
        )

    private fun snapshot(draws: List<Draw>): DrawSnapshot = DrawSnapshot(
        lottery = LotteryType.AZXY10,
        history = draws,
        latest = draws.last(),
        nextPeriod = "21348118",
        sourceHealth = SourceHealth(
            label = "test",
            isFresh = true,
            independentSources = 1,
            message = "test",
            syncedAtEpochMs = 0L,
        ),
    )

    private fun report(snapshot: DrawSnapshot): ForecastReport = ForecastReport(
        algorithmVersion = "test",
        trainedThroughPeriod = snapshot.latest.period,
        targetPeriod = snapshot.nextPeriod,
        historySize = snapshot.history.size,
        validationDraws = 0,
        mode = EvidenceMode.OBSERVE,
        displayUsesShadow = false,
        selectedPosition = 0,
        positions = (0 until 10).map { position ->
            com.tianji.probabilitylab.nativev4.model.PositionPrediction(
                position = position,
                probabilities = List(10) { 0.1 },
                top6 = listOf(1, 2, 3, 4, 5, 6),
                top7 = listOf(1, 2, 3, 4, 5, 6, 7),
                coverage6 = 0.6,
                coverage7 = 0.7,
                boundaryMargin = 0.0,
            )
        },
        models = emptyList(),
        top6HitRate = 0.0,
        top7HitRate = 0.0,
        top6Interval = ConfidenceInterval(0.0, 1.0),
        top7Interval = ConfidenceInterval(0.0, 1.0),
        randomTop6Baseline = 0.6,
        randomTop7Baseline = 0.7,
        breakEvenTop7 = 0.0,
        averageLogLoss = 0.0,
        randomLogLoss = 0.0,
        dataAdequacy = 0,
        blockedReasons = emptyList(),
    )

    private fun draw(period: String, first: Int, fourth: Int): Draw {
        val remaining = (1..10).filterNot { it == first || it == fourth }.toMutableList()
        val numbers = mutableListOf(first)
        numbers += remaining.removeAt(0)
        numbers += remaining.removeAt(0)
        numbers += fourth
        numbers += remaining
        return Draw(
            lottery = LotteryType.AZXY10,
            period = period,
            numbers = numbers,
            source = "test",
        )
    }
}
