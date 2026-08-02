package com.tianji.probabilitylab.nativev4.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class ArchiveCanonicalTest {
    @Test
    fun encodingIsStable() {
        assertEquals(
            ArchiveCanonical.encode("archive-v2", "a", 1, null),
            ArchiveCanonical.encode("archive-v2", "a", 1, null),
        )
    }

    @Test
    fun fieldBoundariesCannotCollide() {
        assertNotEquals(
            ArchiveCanonical.encode("archive-v2", "ab", "c"),
            ArchiveCanonical.encode("archive-v2", "a", "bc"),
        )
    }

    @Test
    fun archiveTypesRemainSeparated() {
        assertNotEquals(
            ArchiveCanonical.encode(ArchiveCanonical.AI_VERSION, "same"),
            ArchiveCanonical.encode(ArchiveCanonical.CONSENSUS_VERSION, "same"),
        )
    }
}
