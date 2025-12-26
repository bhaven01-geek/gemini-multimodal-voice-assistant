import base64
import json
from typing import Optional
import audioop
from pydantic import BaseModel
from pipecat.audio.utils import create_default_resampler
from pipecat.frames.frames import (
   AudioRawFrame,
   Frame,
   InputAudioRawFrame,
   InputDTMFFrame,
   KeypadEntry,
   StartFrame,
   StartInterruptionFrame,
   TransportMessageFrame,
   TransportMessageUrgentFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType




class ExotelSeralizer(FrameSerializer):
   class InputParams(BaseModel):
       exotel_sample_rate: int = 16000  # Default
       sample_rate: Optional[int] = None  # Pipeline input rate


   def __init__(self, stream_sid: str, params: InputParams = InputParams()):
       self._stream_sid = stream_sid
       self._params = params


       self._exotel_sample_rate = self._params.exotel_sample_rate
       self._sample_rate = 0  # Pipeline input rate


       self._resampler = create_default_resampler()


   @property
   def type(self) -> FrameSerializerType:
       return FrameSerializerType.TEXT


   async def setup(self, frame: StartFrame):
       self._sample_rate = self._params.sample_rate or frame.audio_in_sample_rate


   async def serialize(self, frame: Frame) -> str | bytes | None:
       if isinstance(frame, StartInterruptionFrame):
           answer = {"event": "clear", "streamSid": self._stream_sid}
           return json.dumps(answer)
       elif isinstance(frame, AudioRawFrame):
           data = frame.audio
           audio_data, _ = audioop.ratecv(data, 2, 1, 24000, 8000, None)
           con_audio = base64.b64encode(audio_data).decode("ascii")
           answer = {
               "event": "media",
               "streamSid": self._stream_sid,
               "media": {"payload": con_audio},
           }
           return json.dumps(answer)
       elif isinstance(frame, (TransportMessageFrame, TransportMessageUrgentFrame)):
           return json.dumps(frame.message)


   async def deserialize(self, data: str | bytes) -> Frame | None:
       message = json.loads(data)
      
       if message["event"] == "media":
           payload_base64 = message["media"]["payload"]
           payload = base64.b64decode(payload_base64)
           audio_data, _ = audioop.ratecv(payload, 2, 1, 8000, 16000, None)
           audio_frame = InputAudioRawFrame(
               audio=audio_data, num_channels=1, sample_rate=self._sample_rate
           )
           return audio_frame
       elif message["event"] == "dtmf":
           digit = message.get("dtmf", {}).get("digit")


           try:
               return InputDTMFFrame(KeypadEntry(digit))
           except ValueError as e:
               # Handle case where string doesn't match any enum value
               return None
       else:
           return None

